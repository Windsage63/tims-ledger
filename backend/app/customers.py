from __future__ import annotations

import sqlite3

from pydantic import BaseModel, ConfigDict, field_validator

from .date_utils import utc_now


class CustomerWrite(BaseModel):
    customer_name: str
    street_address: str
    city: str
    state: str
    zip: str
    contact_name: str
    email: str
    phone: str
    notes: str | None = ""

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator(
        "customer_name",
        "street_address",
        "city",
        "state",
        "zip",
        "contact_name",
        "email",
        "phone",
    )
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value:
            raise ValueError("This field is required.")
        return value

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str) -> str:
        normalized = value.upper()
        if len(normalized) > 2:
            normalized = normalized[:2]
        return normalized

    @field_validator("notes")
    @classmethod
    def default_notes(cls, value: str | None) -> str:
        return value or ""

    def to_record(self) -> dict[str, str]:
        record = self.model_dump()
        record["notes"] = record["notes"] or ""
        return record

def customer_select_sql() -> str:
    return """
    SELECT
        c.id,
        c.customer_name,
        c.contact_name,
        c.email,
        c.phone,
        c.street_address,
        c.city,
        c.state,
        c.zip,
        COALESCE(c.notes, '') AS notes,
        COALESCE(cb.open_ar_cents, 0) AS open_ar_cents,
        COALESCE(cb.net_balance_cents, 0) AS net_balance_cents,
        c.updated_at
    FROM customers c
    LEFT JOIN customer_balance_view cb ON cb.customer_id = c.id
    """


def row_to_customer(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "customer_name": row["customer_name"],
        "contact_name": row["contact_name"],
        "email": row["email"],
        "phone": row["phone"],
        "street_address": row["street_address"],
        "city": row["city"],
        "state": row["state"],
        "zip": row["zip"],
        "notes": row["notes"],
        "open_ar_cents": row["open_ar_cents"],
        "net_balance_cents": row["net_balance_cents"],
        "updated_at": row["updated_at"],
    }


def fetch_customers(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        customer_select_sql() + " ORDER BY c.customer_name COLLATE NOCASE, c.id"
    ).fetchall()
    return [row_to_customer(row) for row in rows]


def fetch_customer(connection: sqlite3.Connection, customer_id: int) -> dict[str, object] | None:
    row = connection.execute(
        customer_select_sql() + " WHERE c.id = ?",
        (customer_id,),
    ).fetchone()
    if row is None:
        return None
    return row_to_customer(row)


def create_customer(connection: sqlite3.Connection, payload: CustomerWrite) -> dict[str, object]:
    record = payload.to_record()
    timestamp = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO customers (
            customer_name,
            street_address,
            city,
            state,
            zip,
            contact_name,
            email,
            phone,
            notes,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["customer_name"],
            record["street_address"],
            record["city"],
            record["state"],
            record["zip"],
            record["contact_name"],
            record["email"],
            record["phone"],
            record["notes"],
            timestamp,
            timestamp,
        ),
    )
    connection.commit()
    return fetch_customer(connection, cursor.lastrowid)


def update_customer(
    connection: sqlite3.Connection,
    customer_id: int,
    payload: CustomerWrite,
) -> dict[str, object] | None:
    record = payload.to_record()
    cursor = connection.execute(
        """
        UPDATE customers
        SET
            customer_name = ?,
            street_address = ?,
            city = ?,
            state = ?,
            zip = ?,
            contact_name = ?,
            email = ?,
            phone = ?,
            notes = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            record["customer_name"],
            record["street_address"],
            record["city"],
            record["state"],
            record["zip"],
            record["contact_name"],
            record["email"],
            record["phone"],
            record["notes"],
            utc_now(),
            customer_id,
        ),
    )
    if cursor.rowcount == 0:
        connection.rollback()
        return None

    connection.commit()
    return fetch_customer(connection, customer_id)