from __future__ import annotations

import sqlite3

from .data import SUPPORTING_INVOICE_SEED_DATA, TIME_ENTRY_SEED_DATA

from .projects_db import load_projects_db


def load_supporting_invoices_db(connection: sqlite3.Connection) -> int:
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


def load_time_entries_db(connection: sqlite3.Connection) -> int:
    existing_count = connection.execute("SELECT COUNT(*) FROM time_entries").fetchone()[0]
    if existing_count:
        return 0

    load_projects_db(connection)
    load_supporting_invoices_db(connection)
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
