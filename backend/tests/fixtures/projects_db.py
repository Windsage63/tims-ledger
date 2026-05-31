from __future__ import annotations

import sqlite3

from .data import PROJECT_SEED_DATA

from .customers_db import load_customers_db


def load_projects_db(connection: sqlite3.Connection) -> int:
    existing_count = connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    if existing_count:
        return 0

    load_customers_db(connection)

    for row in PROJECT_SEED_DATA:
        connection.execute(
            """
            INSERT INTO projects (
                id,
                project_number,
                customer_id,
                description,
                default_rate_cents,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["project_number"],
                row["customer_id"],
                row["description"],
                next(rate["rate_cents"] for rate in row["rates"] if rate["rate_code"] == "ST"),
                row["updated_at"],
                row["updated_at"],
            ),
        )
        connection.executemany(
            """
            INSERT INTO project_rates (
                id,
                project_id,
                rate_code,
                rate_cents,
                is_builtin,
                sort_order,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    rate["id"],
                    row["id"],
                    rate["rate_code"],
                    rate["rate_cents"],
                    1 if rate["is_builtin"] else 0,
                    rate["sort_order"],
                    row["updated_at"],
                    row["updated_at"],
                )
                for rate in row["rates"]
            ],
        )

    connection.commit()
    return len(PROJECT_SEED_DATA)
