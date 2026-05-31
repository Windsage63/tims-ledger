from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import sqlite3

from pydantic import BaseModel, ConfigDict, field_validator

from .projects import customer_lookup


SUPPORTING_PAYMENT_INVOICE_SEED_DATA = [
    {
        "id": 313,
        "invoice_number": "INV-2026-024",
        "project_id": 33,
        "customer_id": 12,
        "invoice_date": "2026-05-27",
        "terms_days": 30,
        "po_number": None,
        "notes": "Issued to carry remaining permitting and filing costs.",
        "pdf_file_name": "inv-2026-024.pdf",
        "issued_at": "2026-05-27T13:00:00Z",
        "updated_at": "2026-05-27T13:00:00Z",
    },
]


SUPPORTING_PAYMENT_EXPENSE_SEED_DATA = [
    {
        "id": 818,
        "entry_date": "2026-05-27",
        "project_id": 33,
        "customer_id": 12,
        "vendor": "Survey Supply Co.",
        "description": "As-built field book and archival prints.",
        "quantity": 1.0,
        "unit_cost_cents": 42500,
        "line_total_cents": 42500,
        "category": "Supplies",
        "is_billable": True,
        "invoice_id": 313,
        "updated_at": "2026-05-27T13:00:00Z",
    },
]


PAYMENT_SEED_DATA = [
    {
        "id": 68,
        "customer_id": 38,
        "payment_date": "2025-12-30",
        "payment_type": "payment",
        "reference_number": "EFT-188",
        "amount_cents": 78200,
        "notes": "Final payment for meeting materials and site review.",
        "updated_at": "2025-12-30T11:00:00Z",
    },
    {
        "id": 71,
        "customer_id": 12,
        "payment_date": "2026-05-28",
        "payment_type": "advance",
        "reference_number": "CHK-8122",
        "amount_cents": 120000,
        "notes": "Advance retained pending final invoice allocation.",
        "updated_at": "2026-05-31T15:00:00Z",
    },
    {
        "id": 72,
        "customer_id": 19,
        "payment_date": "2026-05-29",
        "payment_type": "payment",
        "reference_number": "ACH-4401",
        "amount_cents": 25000,
        "notes": "Partial ACH receipt.",
        "updated_at": "2026-05-31T15:00:00Z",
    },
    {
        "id": 73,
        "customer_id": 38,
        "payment_date": "2026-05-30",
        "payment_type": "advance",
        "reference_number": "ADV-0017",
        "amount_cents": 15000,
        "notes": "Advance retained for future meeting material work.",
        "updated_at": "2026-05-31T15:00:00Z",
    },
    {
        "id": 74,
        "customer_id": 24,
        "payment_date": "2026-05-30",
        "payment_type": "payment",
        "reference_number": "WIRE-202",
        "amount_cents": 12600,
        "notes": "Wire receipt pending allocation.",
        "updated_at": "2026-05-31T15:00:00Z",
    },
    {
        "id": 75,
        "customer_id": 12,
        "payment_date": "2026-05-31",
        "payment_type": "payment",
        "reference_number": "ACH-9920",
        "amount_cents": 40000,
        "notes": "Second receipt intended for small open balance work.",
        "updated_at": "2026-05-31T15:00:00Z",
    },
]


PAYMENT_APPLICATION_SEED_DATA = [
    {
        "id": 890,
        "payment_id": 68,
        "invoice_id": 188,
        "applied_amount_cents": 78200,
        "applied_at": "2025-12-30T11:05:00Z",
    },
    {
        "id": 902,
        "payment_id": 72,
        "invoice_id": 201,
        "applied_amount_cents": 20000,
        "applied_at": "2026-05-29T14:15:00Z",
    },
    {
        "id": 905,
        "payment_id": 75,
        "invoice_id": 313,
        "applied_amount_cents": 18500,
        "applied_at": "2026-05-31T11:40:00Z",
    },
]


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

    @field_validator("payment_date", "reference_number")
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def derive_due_date(invoice_date: str, terms_days: int) -> str:
    return (date.fromisoformat(invoice_date) + timedelta(days=terms_days)).isoformat()


def payment_status(applied_amount_cents: int, amount_cents: int) -> str:
    if applied_amount_cents <= 0:
        return "unapplied"
    if applied_amount_cents >= amount_cents:
        return "fully_applied"
    return "partially_applied"


def invoice_status(invoice_date: str, terms_days: int, open_balance_cents: int) -> str:
    if open_balance_cents <= 0:
        return "paid"
    if derive_due_date(invoice_date, terms_days) < date.today().isoformat():
        return "overdue"
    return "pending"


def ensure_payment_seed_data(connection: sqlite3.Connection) -> int:
    connection.executemany(
        """
        INSERT INTO invoices (
            id,
            invoice_number,
            project_id,
            customer_id,
            invoice_date,
            terms_days,
            po_number,
            notes,
            pdf_file_name,
            issued_at,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            invoice_number = excluded.invoice_number,
            project_id = excluded.project_id,
            customer_id = excluded.customer_id,
            invoice_date = excluded.invoice_date,
            terms_days = excluded.terms_days,
            po_number = excluded.po_number,
            notes = excluded.notes,
            pdf_file_name = excluded.pdf_file_name,
            issued_at = excluded.issued_at,
            updated_at = excluded.updated_at
        """,
        [
            (
                row["id"],
                row["invoice_number"],
                row["project_id"],
                row["customer_id"],
                row["invoice_date"],
                row["terms_days"],
                row["po_number"],
                row["notes"],
                row["pdf_file_name"],
                row["issued_at"],
                row["updated_at"],
                row["updated_at"],
            )
            for row in SUPPORTING_PAYMENT_INVOICE_SEED_DATA
        ],
    )

    connection.executemany(
        """
        INSERT INTO expenses (
            id,
            entry_date,
            project_id,
            customer_id,
            vendor,
            description,
            quantity,
            unit_cost_cents,
            line_total_cents,
            category,
            is_billable,
            invoice_id,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            entry_date = excluded.entry_date,
            project_id = excluded.project_id,
            customer_id = excluded.customer_id,
            vendor = excluded.vendor,
            description = excluded.description,
            quantity = excluded.quantity,
            unit_cost_cents = excluded.unit_cost_cents,
            line_total_cents = excluded.line_total_cents,
            category = excluded.category,
            is_billable = excluded.is_billable,
            invoice_id = excluded.invoice_id,
            updated_at = excluded.updated_at
        """,
        [
            (
                row["id"],
                row["entry_date"],
                row["project_id"],
                row["customer_id"],
                row["vendor"],
                row["description"],
                row["quantity"],
                row["unit_cost_cents"],
                row["line_total_cents"],
                row["category"],
                1 if row["is_billable"] else 0,
                row["invoice_id"],
                row["updated_at"],
                row["updated_at"],
            )
            for row in SUPPORTING_PAYMENT_EXPENSE_SEED_DATA
        ],
    )

    existing_payment_ids = {
        row["id"] for row in connection.execute("SELECT id FROM payments WHERE id IN (68, 71, 72, 73, 74, 75)").fetchall()
    }
    connection.executemany(
        """
        INSERT INTO payments (
            id,
            customer_id,
            payment_date,
            payment_type,
            reference_number,
            amount_cents,
            notes,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            customer_id = excluded.customer_id,
            payment_date = excluded.payment_date,
            payment_type = excluded.payment_type,
            reference_number = excluded.reference_number,
            amount_cents = excluded.amount_cents,
            notes = excluded.notes,
            updated_at = excluded.updated_at
        """,
        [
            (
                row["id"],
                row["customer_id"],
                row["payment_date"],
                row["payment_type"],
                row["reference_number"],
                row["amount_cents"],
                row["notes"],
                row["updated_at"],
                row["updated_at"],
            )
            for row in PAYMENT_SEED_DATA
        ],
    )

    connection.executemany(
        "DELETE FROM payment_applications WHERE id = ?",
        [(row["id"],) for row in PAYMENT_APPLICATION_SEED_DATA],
    )
    connection.executemany(
        """
        INSERT INTO payment_applications (
            id,
            payment_id,
            invoice_id,
            applied_amount_cents,
            applied_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row["payment_id"],
                row["invoice_id"],
                row["applied_amount_cents"],
                row["applied_at"],
            )
            for row in PAYMENT_APPLICATION_SEED_DATA
        ],
    )
    connection.commit()
    return len([row for row in PAYMENT_SEED_DATA if row["id"] not in existing_payment_ids])


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
            "due_date": derive_due_date(row["invoice_date"], row["terms_days"]),
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