from __future__ import annotations

import sqlite3

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from .date_utils import utc_now


class ProjectRateWrite(BaseModel):
    rate_code: str
    rate_cents: int
    is_builtin: bool = False
    sort_order: int

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("rate_code")
    @classmethod
    def normalize_rate_code(cls, value: str) -> str:
        normalized = value.upper()
        if not normalized:
            raise ValueError("Rate code is required.")
        return normalized

    @field_validator("rate_cents", "sort_order")
    @classmethod
    def non_negative_numbers(cls, value: int) -> int:
        if value < 0:
            raise ValueError("This field must be zero or greater.")
        return value


class ProjectWrite(BaseModel):
    project_number: str
    customer_id: int
    description: str
    default_rate_cents: int
    rates: list[ProjectRateWrite] = []

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("project_number", "description")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value:
            raise ValueError("This field is required.")
        return value

    @field_validator("project_number")
    @classmethod
    def normalize_project_number(cls, value: str) -> str:
        return value.upper()

    @field_validator("customer_id")
    @classmethod
    def positive_customer_id(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Customer is required.")
        return value

    @field_validator("default_rate_cents")
    @classmethod
    def non_negative_default_rate_cents(cls, value: int) -> int:
        if value < 0:
            raise ValueError("This field must be zero or greater.")
        return value

    @model_validator(mode="after")
    def validate_custom_rate_uniqueness(self) -> "ProjectWrite":
        normalized_codes: set[str] = set()
        for rate in self.rates:
            if rate.rate_code in normalized_codes:
                raise ValueError("Rate codes must be unique per project.")
            normalized_codes.add(rate.rate_code)
        return self

def builtin_rates(default_rate_cents: int) -> list[dict[str, object]]:
    return [
        {"rate_code": "ST", "rate_cents": default_rate_cents, "is_builtin": True, "sort_order": 1},
        {"rate_code": "OT", "rate_cents": round(default_rate_cents * 1.5), "is_builtin": True, "sort_order": 2},
        {"rate_code": "TT", "rate_cents": round(default_rate_cents * 0.5), "is_builtin": True, "sort_order": 3},
    ]


def normalize_rates(payload: ProjectWrite) -> list[dict[str, object]]:
    custom_rates: list[dict[str, object]] = []
    seen_codes = {"ST", "OT", "TT"}

    for rate in payload.rates:
        if rate.rate_code in seen_codes:
            continue
        seen_codes.add(rate.rate_code)
        custom_rates.append(
            {
                "rate_code": rate.rate_code,
                "rate_cents": rate.rate_cents,
                "is_builtin": False,
                "sort_order": max(rate.sort_order, 4),
            }
        )

    return builtin_rates(payload.default_rate_cents) + sorted(custom_rates, key=lambda rate: (rate["sort_order"], rate["rate_code"]))


def customer_lookup(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        "SELECT id, customer_name FROM customers ORDER BY customer_name COLLATE NOCASE, id"
    ).fetchall()
    return [{"id": row["id"], "customer_name": row["customer_name"]} for row in rows]


def project_lookup(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT p.id, p.project_number, p.customer_id, c.customer_name, p.description
        FROM projects p
        JOIN customers c ON c.id = p.customer_id
        ORDER BY p.project_number COLLATE NOCASE, p.id
        """
    ).fetchall()
    return [
        {
            "id": row["id"],
            "project_number": row["project_number"],
            "customer_id": row["customer_id"],
            "customer_name": row["customer_name"],
            "description": row["description"],
        }
        for row in rows
    ]


def fetch_project_rates(connection: sqlite3.Connection) -> dict[int, list[dict[str, object]]]:
    rows = connection.execute(
        """
        SELECT id, project_id, rate_code, rate_cents, is_builtin, sort_order
        FROM project_rates
        ORDER BY project_id, sort_order, rate_code, id
        """
    ).fetchall()
    rates_by_project: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        rates_by_project.setdefault(row["project_id"], []).append(
            {
                "id": row["id"],
                "rate_code": row["rate_code"],
                "rate_cents": row["rate_cents"],
                "is_builtin": bool(row["is_builtin"]),
                "sort_order": row["sort_order"],
            }
        )
    return rates_by_project


def row_to_project(row: sqlite3.Row, rates_by_project: dict[int, list[dict[str, object]]]) -> dict[str, object]:
    return {
        "id": row["id"],
        "project_number": row["project_number"],
        "customer_id": row["customer_id"],
        "customer_name": row["customer_name"],
        "description": row["description"],
        "default_rate_cents": row["default_rate_cents"],
        "rates": rates_by_project.get(row["id"], []),
        "spent_to_date_cents": row["spent_to_date_cents"],
        "updated_at": row["updated_at"],
    }


def project_select_sql() -> str:
    return """
    SELECT
        p.id,
        p.project_number,
        p.customer_id,
        c.customer_name,
        p.description,
        p.default_rate_cents,
        p.updated_at,
        COALESCE((
            SELECT SUM(te.line_total_cents)
            FROM time_entries te
            WHERE te.project_id = p.id
        ), 0) + COALESCE((
            SELECT SUM(e.line_total_cents)
            FROM expenses e
            WHERE e.project_id = p.id
        ), 0) AS spent_to_date_cents
    FROM projects p
    JOIN customers c ON c.id = p.customer_id
    """


def fetch_projects(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        project_select_sql() + " ORDER BY p.project_number COLLATE NOCASE, p.id"
    ).fetchall()
    rates_by_project = fetch_project_rates(connection)
    return [row_to_project(row, rates_by_project) for row in rows]


def fetch_project(connection: sqlite3.Connection, project_id: int) -> dict[str, object] | None:
    row = connection.execute(
        project_select_sql() + " WHERE p.id = ?",
        (project_id,),
    ).fetchone()
    if row is None:
        return None
    rates_by_project = fetch_project_rates(connection)
    return row_to_project(row, rates_by_project)


def resolve_customer(connection: sqlite3.Connection, customer_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id, customer_name FROM customers WHERE id = ?",
        (customer_id,),
    ).fetchone()


def insert_project_rates(
    connection: sqlite3.Connection,
    project_id: int,
    rates: list[dict[str, object]],
    *,
    timestamp: str,
) -> None:
    connection.executemany(
        """
        INSERT INTO project_rates (
            project_id,
            rate_code,
            rate_cents,
            is_builtin,
            sort_order,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                project_id,
                rate["rate_code"],
                rate["rate_cents"],
                1 if rate["is_builtin"] else 0,
                rate["sort_order"],
                timestamp,
                timestamp,
            )
            for rate in rates
        ],
    )


def create_project(connection: sqlite3.Connection, payload: ProjectWrite) -> dict[str, object]:
    customer = resolve_customer(connection, payload.customer_id)
    if customer is None:
        raise ValueError("Customer not found.")

    timestamp = utc_now()
    rates = normalize_rates(payload)
    cursor = connection.execute(
        """
        INSERT INTO projects (
            project_number,
            customer_id,
            description,
            default_rate_cents,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payload.project_number,
            payload.customer_id,
            payload.description,
            payload.default_rate_cents,
            timestamp,
            timestamp,
        ),
    )
    insert_project_rates(connection, cursor.lastrowid, rates, timestamp=timestamp)
    connection.commit()
    return fetch_project(connection, cursor.lastrowid)


def update_project(
    connection: sqlite3.Connection,
    project_id: int,
    payload: ProjectWrite,
) -> dict[str, object] | None:
    existing = fetch_project(connection, project_id)
    if existing is None:
        return None

    customer = resolve_customer(connection, payload.customer_id)
    if customer is None:
        raise ValueError("Customer not found.")

    timestamp = utc_now()
    cursor = connection.execute(
        """
        UPDATE projects
        SET
            project_number = ?,
            customer_id = ?,
            description = ?,
            default_rate_cents = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            payload.project_number,
            payload.customer_id,
            payload.description,
            payload.default_rate_cents,
            timestamp,
            project_id,
        ),
    )
    connection.execute("DELETE FROM project_rates WHERE project_id = ?", (project_id,))
    insert_project_rates(connection, project_id, normalize_rates(payload), timestamp=timestamp)
    connection.commit()
    return fetch_project(connection, project_id)
