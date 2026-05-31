from __future__ import annotations

import sqlite3

from .data import CUSTOMER_SEED_DATA


def load_customers_db(connection: sqlite3.Connection) -> int:
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
