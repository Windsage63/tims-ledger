from __future__ import annotations

import sqlite3

from pydantic import BaseModel, ConfigDict, field_validator

from .date_utils import utc_now, validate_iso_date
from .projects import fetch_project_rates, project_lookup


class TimeEntryWrite(BaseModel):
    entry_date: str
    project_id: int
    description: str
    minutes: int
    rate_code: str

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("entry_date")
    @classmethod
    def valid_entry_date(cls, value: str) -> str:
        return validate_iso_date(value, label="Entry date")

    @field_validator("description", "rate_code")
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


def time_entry_select_sql() -> str:
    return """
    SELECT
        te.id,
        te.entry_date,
        te.project_id,
        p.project_number,
        p.description AS project_description,
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
        "project_description": row["project_description"],
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
        """
        SELECT te.invoice_id, i.issued_at
        FROM time_entries te
        LEFT JOIN invoices i ON i.id = te.invoice_id
        WHERE te.id = ?
        """,
        (entry_id,),
    ).fetchone()
    if existing_invoice is None:
        return None
    if existing_invoice["invoice_id"] is not None and existing_invoice["issued_at"] is not None:
        raise ValueError("Time entries on printed invoices are read-only.")

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
