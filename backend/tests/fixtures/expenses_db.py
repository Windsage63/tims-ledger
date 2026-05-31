from __future__ import annotations

import sqlite3

from .data import EXPENSE_SEED_DATA

from .projects_db import load_projects_db
from .time_entries_db import load_supporting_invoices_db


def load_expenses_db(connection: sqlite3.Connection) -> int:
    existing_count = connection.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    if existing_count:
        return 0

    load_projects_db(connection)
    load_supporting_invoices_db(connection)
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
