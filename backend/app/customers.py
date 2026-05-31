from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from pydantic import BaseModel, ConfigDict, field_validator


CUSTOMER_SEED_DATA = [
    {
        "id": 12,
        "customer_name": "Acme Corp.",
        "contact_name": "Jane Smith",
        "email": "jane@acme.com",
        "phone": "555-0100",
        "street_address": "123 Main St.",
        "city": "Austin",
        "state": "TX",
        "zip": "78701",
        "notes": "Prefers email invoices. Main municipal review client.",
        "updated_at": "2026-05-31T15:00:00Z",
    },
    {
        "id": 19,
        "customer_name": "Nexa Synergy Group",
        "contact_name": "Sarah Jenkins",
        "email": "sjenkins@nexa.example",
        "phone": "555-0133",
        "street_address": "80 Lakeview Ave.",
        "city": "Denver",
        "state": "CO",
        "zip": "80202",
        "notes": "Usually approves quickly. Wants invoices grouped by project.",
        "updated_at": "2026-05-30T11:20:00Z",
    },
    {
        "id": 24,
        "customer_name": "Horizon Ventures",
        "contact_name": "Michael Chen",
        "email": "mchen@horizon.example",
        "phone": "555-0188",
        "street_address": "500 8th Street",
        "city": "Boise",
        "state": "ID",
        "zip": "83702",
        "notes": "Late payer. Track follow-up carefully.",
        "updated_at": "2026-05-28T08:15:00Z",
    },
    {
        "id": 31,
        "customer_name": "Aura Design Studio",
        "contact_name": "Elena Rodriguez",
        "email": "elena@aura.example",
        "phone": "555-0112",
        "street_address": "44 Pearl Lane",
        "city": "Santa Fe",
        "state": "NM",
        "zip": "87501",
        "notes": "Pending invoice review on current project.",
        "updated_at": "2026-05-31T09:40:00Z",
    },
    {
        "id": 38,
        "customer_name": "Granite Public Works",
        "contact_name": "Lewis Patel",
        "email": "lpatel@granite.example",
        "phone": "555-0174",
        "street_address": "900 Civic Center Dr.",
        "city": "Madison",
        "state": "WI",
        "zip": "53703",
        "notes": "Government client. Keep PO references prominent.",
        "updated_at": "2026-05-29T16:55:00Z",
    },
    {
        "id": 44,
        "customer_name": "Summit Habitat Collective",
        "contact_name": "Priya Nand",
        "email": "priya@summit.example",
        "phone": "555-0191",
        "street_address": "12 Ridge Road",
        "city": "Bend",
        "state": "OR",
        "zip": "97701",
        "notes": "Inactive but preserve history for prior drainage work.",
        "updated_at": "2026-04-18T13:10:00Z",
    },
]


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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def ensure_customer_seed_data(connection: sqlite3.Connection) -> int:
    existing_count = connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    if existing_count:
        return 0

    connection.executemany(
        """
        INSERT INTO customers (
            id,
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row["customer_name"],
                row["street_address"],
                row["city"],
                row["state"],
                row["zip"],
                row["contact_name"],
                row["email"],
                row["phone"],
                row["notes"],
                row["updated_at"],
                row["updated_at"],
            )
            for row in CUSTOMER_SEED_DATA
        ],
    )
    connection.commit()
    return len(CUSTOMER_SEED_DATA)


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