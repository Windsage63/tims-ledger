from __future__ import annotations

import sqlite3

from pydantic import BaseModel, ConfigDict, field_validator

from .date_utils import utc_now, validate_iso_date
from .projects import customer_lookup


class PaymentWrite(BaseModel):
    customer_id: int
    payment_date: str
    payment_type: str
    reference_number: str
    amount_cents: int
    notes: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("customer_id")
    @classmethod
    def positive_customer_id(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Customer is required.")
        return value

    @field_validator("payment_date")
    @classmethod
    def valid_payment_date(cls, value: str) -> str:
        return validate_iso_date(value, label="Payment date")

    @field_validator("reference_number")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value:
            raise ValueError("This field is required.")
        return value

    @field_validator("payment_type")
    @classmethod
    def valid_payment_type(cls, value: str) -> str:
        if value not in {"payment", "advance"}:
            raise ValueError("Payment type must be payment or advance.")
        return value

    @field_validator("amount_cents")
    @classmethod
    def positive_amount(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Amount must be greater than zero.")
        return value


class PaymentApplicationWrite(BaseModel):
    invoice_id: int
    applied_amount_cents: int

    @field_validator("invoice_id")
    @classmethod
    def positive_invoice_id(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Invoice is required.")
        return value

    @field_validator("applied_amount_cents")
    @classmethod
    def positive_applied_amount(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Applied amount must be greater than zero.")
        return value


class PaymentApplicationsReplace(BaseModel):
    applications: list[PaymentApplicationWrite]

def payment_status(applied_amount_cents: int, amount_cents: int) -> str:
    if applied_amount_cents <= 0:
        return "unapplied"
    if applied_amount_cents >= amount_cents:
        return "fully_applied"
    return "partially_applied"


def invoice_status(invoice_date: str, terms_days: int, open_balance_cents: int) -> str:
    if open_balance_cents <= 0:
        return "paid"
    return "pending"


def payment_select_sql() -> str:
    return """
    SELECT
        p.id,
        p.customer_id,
        c.customer_name,
        p.payment_date,
        p.payment_type,
        p.reference_number,
        p.amount_cents,
        p.notes,
        p.updated_at,
        COALESCE(puv.applied_amount_cents, 0) AS applied_amount_cents,
        COALESCE(puv.unapplied_amount_cents, p.amount_cents) AS unapplied_amount_cents
    FROM payments p
    JOIN customers c ON c.id = p.customer_id
    LEFT JOIN payment_unapplied_view puv ON puv.payment_id = p.id
    """


def row_to_payment(row: sqlite3.Row) -> dict[str, object]:
    applied_amount_cents = int(row["applied_amount_cents"])
    amount_cents = int(row["amount_cents"])
    return {
        "id": row["id"],
        "customer_id": row["customer_id"],
        "customer_name": row["customer_name"],
        "payment_date": row["payment_date"],
        "payment_type": row["payment_type"],
        "reference_number": row["reference_number"],
        "amount_cents": amount_cents,
        "applied_amount_cents": applied_amount_cents,
        "unapplied_amount_cents": int(row["unapplied_amount_cents"]),
        "application_status": payment_status(applied_amount_cents, amount_cents),
        "notes": row["notes"],
        "updated_at": row["updated_at"],
    }


def fetch_payments(connection: sqlite3.Connection, year: str | None = None) -> list[dict[str, object]]:
    sql = payment_select_sql()
    parameters: list[object] = []
    if year:
        sql += " WHERE substr(p.payment_date, 1, 4) = ?"
        parameters.append(year)
    sql += " ORDER BY p.payment_date DESC, p.id DESC"
    rows = connection.execute(sql, parameters).fetchall()
    return [row_to_payment(row) for row in rows]


def fetch_payment(connection: sqlite3.Connection, payment_id: int) -> dict[str, object] | None:
    row = connection.execute(payment_select_sql() + " WHERE p.id = ?", (payment_id,)).fetchone()
    if row is None:
        return None
    return row_to_payment(row)


def fetch_applications(connection: sqlite3.Connection, payment_id: int) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            pa.id,
            pa.payment_id,
            pa.invoice_id,
            i.invoice_number,
            pa.applied_amount_cents,
            pa.applied_at
        FROM payment_applications pa
        JOIN invoices i ON i.id = pa.invoice_id
        WHERE pa.payment_id = ?
        ORDER BY pa.applied_at DESC, pa.id DESC
        """,
        (payment_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_open_invoices(connection: sqlite3.Connection, payment: dict[str, object]) -> list[dict[str, object]]:
    current_applications = {
        row["invoice_id"]: row["applied_amount_cents"]
        for row in connection.execute(
            "SELECT invoice_id, applied_amount_cents FROM payment_applications WHERE payment_id = ?",
            (payment["id"],),
        ).fetchall()
    }
    rows = connection.execute(
        """
        SELECT
            i.id,
            i.invoice_number,
            i.invoice_date,
            i.terms_days,
            COALESCE(ibv.invoice_amount_cents, 0) AS invoice_amount_cents,
            COALESCE(ibv.paid_amount_cents, 0) AS paid_amount_cents,
            COALESCE(ibv.open_amount_cents, 0) AS open_balance_cents
        FROM invoices i
        LEFT JOIN invoice_balance_view ibv ON ibv.invoice_id = i.id
        WHERE i.customer_id = ? AND i.issued_at IS NOT NULL
        ORDER BY i.invoice_date DESC, i.id DESC
        """,
        (payment["customer_id"],),
    ).fetchall()

    open_invoices: list[dict[str, object]] = []
    for row in rows:
        current_applied_cents = int(current_applications.get(row["id"], 0))
        open_balance_cents = int(row["open_balance_cents"])
        if open_balance_cents <= 0 and current_applied_cents <= 0:
            continue
        invoice = {
            "id": row["id"],
            "invoice_number": row["invoice_number"],
            "invoice_date": row["invoice_date"],
            "terms_days": row["terms_days"],
            "invoice_amount_cents": int(row["invoice_amount_cents"]),
            "paid_amount_cents": int(row["paid_amount_cents"]),
            "open_balance_cents": open_balance_cents,
            "status": invoice_status(row["invoice_date"], row["terms_days"], open_balance_cents),
            "current_applied_cents": current_applied_cents,
            "available_to_apply_cents": open_balance_cents + current_applied_cents,
        }
        open_invoices.append(invoice)
    return open_invoices


def payment_editor_payload(connection: sqlite3.Connection, payment_id: int) -> dict[str, object] | None:
    payment = fetch_payment(connection, payment_id)
    if payment is None:
        return None
    return {
        "payment": payment,
        "applications": fetch_applications(connection, payment_id),
        "open_invoices": fetch_open_invoices(connection, payment),
    }


def payments_bootstrap_payload(connection: sqlite3.Connection, year: str | None = None) -> dict[str, object]:
    return {
        "payments": fetch_payments(connection, year=year),
        "customers": customer_lookup(connection),
    }


def resolve_customer(connection: sqlite3.Connection, customer_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id, customer_name FROM customers WHERE id = ?",
        (customer_id,),
    ).fetchone()


def create_payment(connection: sqlite3.Connection, payload: PaymentWrite) -> dict[str, object]:
    customer = resolve_customer(connection, payload.customer_id)
    if customer is None:
        raise ValueError("Customer not found.")
    timestamp = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO payments (
            customer_id,
            payment_date,
            payment_type,
            reference_number,
            amount_cents,
            notes,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.customer_id,
            payload.payment_date,
            payload.payment_type,
            payload.reference_number,
            payload.amount_cents,
            payload.notes,
            timestamp,
            timestamp,
        ),
    )
    connection.commit()
    payment = fetch_payment(connection, cursor.lastrowid)
    if payment is None:
        raise ValueError("Payment could not be loaded after creation.")
    return payment


def update_payment(connection: sqlite3.Connection, payment_id: int, payload: PaymentWrite) -> dict[str, object] | None:
    existing = fetch_payment(connection, payment_id)
    if existing is None:
        return None
    customer = resolve_customer(connection, payload.customer_id)
    if customer is None:
        raise ValueError("Customer not found.")
    if int(existing["applied_amount_cents"]) > payload.amount_cents:
        raise ValueError("Amount cannot be less than currently applied total.")
    if payload.customer_id != existing["customer_id"]:
        connection.execute("DELETE FROM payment_applications WHERE payment_id = ?", (payment_id,))
    connection.execute(
        """
        UPDATE payments
        SET
            customer_id = ?,
            payment_date = ?,
            payment_type = ?,
            reference_number = ?,
            amount_cents = ?,
            notes = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            payload.customer_id,
            payload.payment_date,
            payload.payment_type,
            payload.reference_number,
            payload.amount_cents,
            payload.notes,
            utc_now(),
            payment_id,
        ),
    )
    connection.commit()
    return fetch_payment(connection, payment_id)


def replace_payment_applications(
    connection: sqlite3.Connection,
    payment_id: int,
    payload: PaymentApplicationsReplace,
) -> dict[str, object] | None:
    payment = fetch_payment(connection, payment_id)
    if payment is None:
        return None

    requested = payload.applications
    if len({application.invoice_id for application in requested}) != len(requested):
        raise ValueError("Applications must target each invoice at most once.")

    total_requested = sum(application.applied_amount_cents for application in requested)
    if total_requested > int(payment["amount_cents"]):
        raise ValueError("Applications cannot exceed the payment amount.")

    current_map = {
        row["invoice_id"]: row["applied_amount_cents"]
        for row in connection.execute(
            "SELECT invoice_id, applied_amount_cents FROM payment_applications WHERE payment_id = ?",
            (payment_id,),
        ).fetchall()
    }
    open_invoices = {invoice["id"]: invoice for invoice in fetch_open_invoices(connection, payment)}
    for application in requested:
        invoice = open_invoices.get(application.invoice_id)
        if invoice is None:
            raise ValueError("Application invoice is not available for this payment.")
        max_allowed = int(invoice["open_balance_cents"]) + int(current_map.get(application.invoice_id, 0))
        if application.applied_amount_cents > max_allowed:
            raise ValueError("Application amount exceeds the available balance for an invoice.")

    connection.execute("DELETE FROM payment_applications WHERE payment_id = ?", (payment_id,))
    next_id_row = connection.execute("SELECT COALESCE(MAX(id), 900) AS max_id FROM payment_applications").fetchone()
    next_id = int(next_id_row["max_id"]) + 1
    timestamp = utc_now()
    for application in requested:
        connection.execute(
            """
            INSERT INTO payment_applications (
                id,
                payment_id,
                invoice_id,
                applied_amount_cents,
                applied_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                next_id,
                payment_id,
                application.invoice_id,
                application.applied_amount_cents,
                timestamp,
            ),
        )
        next_id += 1
    connection.commit()
    return payment_editor_payload(connection, payment_id)