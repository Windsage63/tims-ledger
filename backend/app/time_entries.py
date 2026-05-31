from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from pydantic import BaseModel, ConfigDict, field_validator

from .projects import fetch_project_rates, project_lookup


SUPPORTING_INVOICE_SEED_DATA = [
    {
        "id": 201,
        "invoice_number": "INV-2026-014",
        "project_id": 34,
        "customer_id": 19,
        "invoice_date": "2026-05-20",
        "terms_days": 31,
        "po_number": None,
        "notes": "Seeded to preserve invoice linkage for time entries.",
        "issued_at": "2026-05-20T14:12:00Z",
        "updated_at": "2026-05-20T14:12:00Z",
    },
    {
        "id": 205,
        "invoice_number": "INV-2026-019",
        "project_id": 35,
        "customer_id": 24,
        "invoice_date": "2026-05-21",
        "terms_days": 8,
        "po_number": None,
        "notes": "Seeded to preserve invoice linkage for expense rows.",
        "issued_at": "2026-05-21T11:00:00Z",
        "updated_at": "2026-05-21T11:00:00Z",
    },
    {
        "id": 188,
        "invoice_number": "INV-2025-098",
        "project_id": 37,
        "customer_id": 38,
        "invoice_date": "2025-12-17",
        "terms_days": 30,
        "po_number": "PW-44",
        "notes": "Seeded to preserve invoice linkage for time entries.",
        "issued_at": "2025-12-17T09:00:00Z",
        "updated_at": "2025-12-17T09:00:00Z",
    },
]


TIME_ENTRY_SEED_DATA = [
    {
        "id": 401,
        "entry_date": "2026-05-20",
        "project_id": 33,
        "customer_id": 12,
        "description": "Drainage calculations and detention memo updates.",
        "minutes": 270,
        "rate_code": "ST",
        "rate_cents": 12500,
        "line_total_cents": 56250,
        "invoice_id": None,
        "updated_at": "2026-05-31T15:00:00Z",
    },
    {
        "id": 402,
        "entry_date": "2026-05-21",
        "project_id": 33,
        "customer_id": 12,
        "description": "Fixed-fee billing marker for permit package issuance.",
        "minutes": 60,
        "rate_code": "FF1",
        "rate_cents": 250000,
        "line_total_cents": 250000,
        "invoice_id": None,
        "updated_at": "2026-05-31T15:00:00Z",
    },
    {
        "id": 403,
        "entry_date": "2026-05-22",
        "project_id": 34,
        "customer_id": 19,
        "description": "Subdivision grading revisions after client review.",
        "minutes": 195,
        "rate_code": "OT",
        "rate_cents": 20700,
        "line_total_cents": 67275,
        "invoice_id": 201,
        "updated_at": "2026-05-30T12:10:00Z",
    },
    {
        "id": 404,
        "entry_date": "2026-05-23",
        "project_id": 35,
        "customer_id": 24,
        "description": "Site visit and field sketch compilation.",
        "minutes": 210,
        "rate_code": "SITE",
        "rate_cents": 11000,
        "line_total_cents": 38500,
        "invoice_id": None,
        "updated_at": "2026-05-27T14:10:00Z",
    },
    {
        "id": 405,
        "entry_date": "2026-05-24",
        "project_id": 35,
        "customer_id": 24,
        "description": "Internal coordination meeting and archived reference note cleanup.",
        "minutes": 75,
        "rate_code": "NB",
        "rate_cents": 0,
        "line_total_cents": 0,
        "invoice_id": None,
        "updated_at": "2026-05-27T14:12:00Z",
    },
    {
        "id": 406,
        "entry_date": "2025-12-16",
        "project_id": 37,
        "customer_id": 38,
        "description": "Public meeting board updates and storm line profile review.",
        "minutes": 300,
        "rate_code": "ST",
        "rate_cents": 14500,
        "line_total_cents": 72500,
        "invoice_id": 188,
        "updated_at": "2025-12-17T09:00:00Z",
    },
]


class TimeEntryWrite(BaseModel):
    entry_date: str
    project_id: int
    description: str
    minutes: int
    rate_code: str

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("entry_date", "description", "rate_code")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value:
            raise ValueError("This field is required.")
        return value

    @field_validator("minutes")
    @classmethod
    def positive_minutes(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Minutes must be greater than zero.")
        return value

    @field_validator("project_id")
    @classmethod
    def positive_project_id(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Project is required.")
        return value

    @field_validator("rate_code")
    @classmethod
    def normalize_rate_code(cls, value: str) -> str:
        return value.upper()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_supporting_invoice_seed_data(connection: sqlite3.Connection) -> int:
    inserted = 0
    for row in SUPPORTING_INVOICE_SEED_DATA:
        exists = connection.execute(
            "SELECT 1 FROM invoices WHERE id = ? OR invoice_number = ?",
            (row["id"], row["invoice_number"]),
        ).fetchone()
        if exists is not None:
            continue

        connection.execute(
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
            """,
            (
                row["id"],
                row["invoice_number"],
                row["project_id"],
                row["customer_id"],
                row["invoice_date"],
                row["terms_days"],
                row["po_number"],
                row["notes"],
                None,
                row["issued_at"],
                row["updated_at"],
                row["updated_at"],
            ),
        )
        inserted += 1

    if inserted:
        connection.commit()
    return inserted


def ensure_time_entry_seed_data(connection: sqlite3.Connection) -> int:
    existing_count = connection.execute("SELECT COUNT(*) FROM time_entries").fetchone()[0]
    if existing_count:
        return 0

    ensure_supporting_invoice_seed_data(connection)
    connection.executemany(
        """
        INSERT INTO time_entries (
            id,
            entry_date,
            project_id,
            customer_id,
            description,
            minutes,
            rate_code,
            rate_cents,
            line_total_cents,
            invoice_id,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row["entry_date"],
                row["project_id"],
                row["customer_id"],
                row["description"],
                row["minutes"],
                row["rate_code"],
                row["rate_cents"],
                row["line_total_cents"],
                row["invoice_id"],
                row["updated_at"],
                row["updated_at"],
            )
            for row in TIME_ENTRY_SEED_DATA
        ],
    )
    connection.commit()
    return len(TIME_ENTRY_SEED_DATA)


def time_entry_select_sql() -> str:
    return """
    SELECT
        te.id,
        te.entry_date,
        te.project_id,
        p.project_number,
        te.customer_id,
        c.customer_name,
        te.description,
        te.minutes,
        te.rate_code,
        te.rate_cents,
        te.line_total_cents,
        i.invoice_number,
        te.updated_at
    FROM time_entries te
    JOIN projects p ON p.id = te.project_id
    JOIN customers c ON c.id = te.customer_id
    LEFT JOIN invoices i ON i.id = te.invoice_id
    """


def row_to_time_entry(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "entry_date": row["entry_date"],
        "project_id": row["project_id"],
        "project_number": row["project_number"],
        "customer_id": row["customer_id"],
        "customer_name": row["customer_name"],
        "description": row["description"],
        "minutes": row["minutes"],
        "rate_code": row["rate_code"],
        "rate_cents": row["rate_cents"],
        "line_total_cents": row["line_total_cents"],
        "invoice_number": row["invoice_number"],
        "updated_at": row["updated_at"],
    }


def fetch_time_entries(connection: sqlite3.Connection, year: str | None = None) -> list[dict[str, object]]:
    sql = time_entry_select_sql()
    parameters: list[object] = []
    if year:
        sql += " WHERE substr(te.entry_date, 1, 4) = ?"
        parameters.append(year)
    sql += " ORDER BY te.entry_date DESC, te.id DESC"

    rows = connection.execute(sql, parameters).fetchall()
    return [row_to_time_entry(row) for row in rows]


def fetch_time_entry(connection: sqlite3.Connection, entry_id: int) -> dict[str, object] | None:
    row = connection.execute(
        time_entry_select_sql() + " WHERE te.id = ?",
        (entry_id,),
    ).fetchone()
    if row is None:
        return None
    return row_to_time_entry(row)


def resolve_project_rate(
    connection: sqlite3.Connection,
    project_id: int,
    rate_code: str,
) -> tuple[sqlite3.Row | None, dict[str, object] | None]:
    project_row = connection.execute(
        """
        SELECT p.id, p.project_number, p.customer_id, c.customer_name
        FROM projects p
        JOIN customers c ON c.id = p.customer_id
        WHERE p.id = ?
        """,
        (project_id,),
    ).fetchone()
    if project_row is None:
        return None, None

    rate_row = connection.execute(
        """
        SELECT rate_code, rate_cents
        FROM project_rates
        WHERE project_id = ? AND rate_code = ?
        """,
        (project_id, rate_code),
    ).fetchone()
    if rate_row is None:
        return project_row, None

    return project_row, {
        "rate_code": rate_row["rate_code"],
        "rate_cents": rate_row["rate_cents"],
    }


def create_time_entry(connection: sqlite3.Connection, payload: TimeEntryWrite) -> dict[str, object]:
    project_row, rate = resolve_project_rate(connection, payload.project_id, payload.rate_code)
    if project_row is None or rate is None:
        raise ValueError("Project or rate code not found.")

    timestamp = utc_now()
    line_total_cents = round(payload.minutes * rate["rate_cents"] / 60)
    cursor = connection.execute(
        """
        INSERT INTO time_entries (
            entry_date,
            project_id,
            customer_id,
            description,
            minutes,
            rate_code,
            rate_cents,
            line_total_cents,
            invoice_id,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.entry_date,
            payload.project_id,
            project_row["customer_id"],
            payload.description,
            payload.minutes,
            rate["rate_code"],
            rate["rate_cents"],
            line_total_cents,
            None,
            timestamp,
            timestamp,
        ),
    )
    connection.commit()
    return fetch_time_entry(connection, cursor.lastrowid)


def update_time_entry(
    connection: sqlite3.Connection,
    entry_id: int,
    payload: TimeEntryWrite,
) -> dict[str, object] | None:
    existing_invoice = connection.execute(
        "SELECT invoice_id FROM time_entries WHERE id = ?",
        (entry_id,),
    ).fetchone()
    if existing_invoice is None:
        return None

    project_row, rate = resolve_project_rate(connection, payload.project_id, payload.rate_code)
    if project_row is None or rate is None:
        raise ValueError("Project or rate code not found.")

    line_total_cents = round(payload.minutes * rate["rate_cents"] / 60)
    connection.execute(
        """
        UPDATE time_entries
        SET
            entry_date = ?,
            project_id = ?,
            customer_id = ?,
            description = ?,
            minutes = ?,
            rate_code = ?,
            rate_cents = ?,
            line_total_cents = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            payload.entry_date,
            payload.project_id,
            project_row["customer_id"],
            payload.description,
            payload.minutes,
            rate["rate_code"],
            rate["rate_cents"],
            line_total_cents,
            utc_now(),
            entry_id,
        ),
    )
    connection.commit()
    return fetch_time_entry(connection, entry_id)


def time_bootstrap_payload(connection: sqlite3.Connection, year: str | None = None) -> dict[str, object]:
    customer_rows = connection.execute(
        "SELECT id, customer_name FROM customers ORDER BY customer_name COLLATE NOCASE, id"
    ).fetchall()
    return {
        "entries": fetch_time_entries(connection, year=year),
        "projects": project_lookup(connection),
        "customers": [{"id": row["id"], "customer_name": row["customer_name"]} for row in customer_rows],
        "rates_by_project": fetch_project_rates(connection),
    }