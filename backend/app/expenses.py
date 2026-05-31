from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from pydantic import BaseModel, ConfigDict, field_validator

from .projects import customer_lookup, project_lookup
from .time_entries import ensure_supporting_invoice_seed_data


EXPENSE_CATEGORIES = [
    "Equipment",
    "Meals",
    "Mileage",
    "Permits",
    "Printing",
    "Records",
    "Supplies",
    "Travel",
]


EXPENSE_SEED_DATA = [
    {
        "id": 812,
        "entry_date": "2026-05-19",
        "project_id": 33,
        "customer_id": 12,
        "vendor": "County Recorder",
        "description": "Map copy fee",
        "quantity": 2.0,
        "unit_cost_cents": 1500,
        "line_total_cents": 3000,
        "category": "Records",
        "is_billable": True,
        "invoice_id": None,
        "updated_at": "2026-05-31T15:00:00Z",
    },
    {
        "id": 813,
        "entry_date": "2026-05-21",
        "project_id": 35,
        "customer_id": 24,
        "vendor": "United Rentals",
        "description": "Laser level rental for drainage retrofit staking.",
        "quantity": 3.0,
        "unit_cost_cents": 4200,
        "line_total_cents": 12600,
        "category": "Equipment",
        "is_billable": True,
        "invoice_id": 205,
        "updated_at": "2026-05-29T11:10:00Z",
    },
    {
        "id": 814,
        "entry_date": "2026-05-23",
        "project_id": 36,
        "customer_id": 31,
        "vendor": "Corner Cafe",
        "description": "Internal design workshop lunch.",
        "quantity": 4.0,
        "unit_cost_cents": 1800,
        "line_total_cents": 7200,
        "category": "Meals",
        "is_billable": False,
        "invoice_id": None,
        "updated_at": "2026-05-27T08:40:00Z",
    },
    {
        "id": 815,
        "entry_date": "2026-05-24",
        "project_id": 34,
        "customer_id": 19,
        "vendor": "State Permit Office",
        "description": "Subdivision review filing fee.",
        "quantity": 1.0,
        "unit_cost_cents": 18500,
        "line_total_cents": 18500,
        "category": "Permits",
        "is_billable": True,
        "invoice_id": None,
        "updated_at": "2026-05-30T09:15:00Z",
    },
    {
        "id": 816,
        "entry_date": "2026-05-26",
        "project_id": 37,
        "customer_id": 38,
        "vendor": "FedEx Office",
        "description": "Meeting board print set.",
        "quantity": 6.0,
        "unit_cost_cents": 950,
        "line_total_cents": 5700,
        "category": "Printing",
        "is_billable": True,
        "invoice_id": 188,
        "updated_at": "2026-05-26T16:30:00Z",
    },
    {
        "id": 817,
        "entry_date": "2025-12-14",
        "project_id": 37,
        "customer_id": 38,
        "vendor": "Fuel Card",
        "description": "Site mileage reimbursement.",
        "quantity": 86.0,
        "unit_cost_cents": 67,
        "line_total_cents": 5762,
        "category": "Mileage",
        "is_billable": True,
        "invoice_id": None,
        "updated_at": "2025-12-15T10:05:00Z",
    },
]


class ExpenseWrite(BaseModel):
    entry_date: str
    project_id: int
    vendor: str
    description: str
    quantity: float
    unit_cost_cents: int
    category: str
    is_billable: bool

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("entry_date", "vendor", "description", "category")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value:
            raise ValueError("This field is required.")
        return value

    @field_validator("project_id")
    @classmethod
    def positive_project_id(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Project is required.")
        return value

    @field_validator("quantity")
    @classmethod
    def positive_quantity(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Quantity must be greater than zero.")
        return value

    @field_validator("unit_cost_cents")
    @classmethod
    def non_negative_unit_cost(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Unit cost must be zero or greater.")
        return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_expense_seed_data(connection: sqlite3.Connection) -> int:
    existing_count = connection.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    if existing_count:
        return 0

    ensure_supporting_invoice_seed_data(connection)
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
            for row in EXPENSE_SEED_DATA
        ],
    )
    connection.commit()
    return len(EXPENSE_SEED_DATA)


def expense_select_sql() -> str:
    return """
    SELECT
        e.id,
        e.entry_date,
        e.project_id,
        p.project_number,
        e.customer_id,
        c.customer_name,
        e.vendor,
        e.description,
        e.quantity,
        e.unit_cost_cents,
        e.line_total_cents,
        e.category,
        e.is_billable,
        i.invoice_number,
        e.updated_at
    FROM expenses e
    JOIN projects p ON p.id = e.project_id
    JOIN customers c ON c.id = e.customer_id
    LEFT JOIN invoices i ON i.id = e.invoice_id
    """


def row_to_expense(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "entry_date": row["entry_date"],
        "project_id": row["project_id"],
        "project_number": row["project_number"],
        "customer_id": row["customer_id"],
        "customer_name": row["customer_name"],
        "vendor": row["vendor"],
        "description": row["description"],
        "quantity": row["quantity"],
        "unit_cost_cents": row["unit_cost_cents"],
        "line_total_cents": row["line_total_cents"],
        "category": row["category"],
        "is_billable": bool(row["is_billable"]),
        "invoice_number": row["invoice_number"],
        "updated_at": row["updated_at"],
    }


def fetch_expenses(connection: sqlite3.Connection, year: str | None = None) -> list[dict[str, object]]:
    sql = expense_select_sql()
    parameters: list[object] = []
    if year:
        sql += " WHERE substr(e.entry_date, 1, 4) = ?"
        parameters.append(year)
    sql += " ORDER BY e.entry_date DESC, e.id DESC"

    rows = connection.execute(sql, parameters).fetchall()
    return [row_to_expense(row) for row in rows]


def fetch_expense(connection: sqlite3.Connection, expense_id: int) -> dict[str, object] | None:
    row = connection.execute(
        expense_select_sql() + " WHERE e.id = ?",
        (expense_id,),
    ).fetchone()
    if row is None:
        return None
    return row_to_expense(row)


def resolve_project_customer(connection: sqlite3.Connection, project_id: int) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT p.id, p.project_number, p.customer_id, c.customer_name
        FROM projects p
        JOIN customers c ON c.id = p.customer_id
        WHERE p.id = ?
        """,
        (project_id,),
    ).fetchone()


def create_expense(connection: sqlite3.Connection, payload: ExpenseWrite) -> dict[str, object]:
    project_row = resolve_project_customer(connection, payload.project_id)
    if project_row is None:
        raise ValueError("Project not found.")

    timestamp = utc_now()
    line_total_cents = round(payload.quantity * payload.unit_cost_cents)
    cursor = connection.execute(
        """
        INSERT INTO expenses (
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.entry_date,
            payload.project_id,
            project_row["customer_id"],
            payload.vendor,
            payload.description,
            payload.quantity,
            payload.unit_cost_cents,
            line_total_cents,
            payload.category,
            1 if payload.is_billable else 0,
            None,
            timestamp,
            timestamp,
        ),
    )
    connection.commit()
    return fetch_expense(connection, cursor.lastrowid)


def update_expense(
    connection: sqlite3.Connection,
    expense_id: int,
    payload: ExpenseWrite,
) -> dict[str, object] | None:
    existing = connection.execute(
        "SELECT invoice_id FROM expenses WHERE id = ?",
        (expense_id,),
    ).fetchone()
    if existing is None:
        return None

    project_row = resolve_project_customer(connection, payload.project_id)
    if project_row is None:
        raise ValueError("Project not found.")

    line_total_cents = round(payload.quantity * payload.unit_cost_cents)
    connection.execute(
        """
        UPDATE expenses
        SET
            entry_date = ?,
            project_id = ?,
            customer_id = ?,
            vendor = ?,
            description = ?,
            quantity = ?,
            unit_cost_cents = ?,
            line_total_cents = ?,
            category = ?,
            is_billable = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            payload.entry_date,
            payload.project_id,
            project_row["customer_id"],
            payload.vendor,
            payload.description,
            payload.quantity,
            payload.unit_cost_cents,
            line_total_cents,
            payload.category,
            1 if payload.is_billable else 0,
            utc_now(),
            expense_id,
        ),
    )
    connection.commit()
    return fetch_expense(connection, expense_id)


def expense_categories(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT DISTINCT category FROM expenses WHERE category IS NOT NULL AND category != '' ORDER BY category COLLATE NOCASE"
    ).fetchall()
    seen = set()
    ordered: list[str] = []
    for category in EXPENSE_CATEGORIES:
        if category not in seen:
            ordered.append(category)
            seen.add(category)
    for row in rows:
        category = row["category"]
        if category not in seen:
            ordered.append(category)
            seen.add(category)
    return ordered


def expense_bootstrap_payload(connection: sqlite3.Connection, year: str | None = None) -> dict[str, object]:
    return {
        "expenses": fetch_expenses(connection, year=year),
        "projects": project_lookup(connection),
        "customers": customer_lookup(connection),
        "categories": expense_categories(connection),
    }