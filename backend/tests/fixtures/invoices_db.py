from __future__ import annotations

import sqlite3

from .data import (
    INVOICE_SEED_DATA,
    SUPPORTING_INVOICE_TIME_ENTRY_SEED_DATA,
    SUPPORTING_PAYMENT_APPLICATION_SEED_DATA,
    SUPPORTING_PAYMENT_SEED_DATA,
)

from .expenses_db import load_expenses_db
from .projects_db import load_projects_db
from .time_entries_db import load_time_entries_db


def load_invoices_db(connection: sqlite3.Connection) -> int:
    already_seeded = connection.execute("SELECT 1 FROM invoices WHERE id = 301").fetchone()
    if already_seeded is not None:
        return 0

    load_projects_db(connection)
    load_time_entries_db(connection)
    load_expenses_db(connection)

    connection.executemany(
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
        ON CONFLICT(id) DO UPDATE SET
            invoice_number = excluded.invoice_number,
            project_id = excluded.project_id,
            customer_id = excluded.customer_id,
            invoice_date = excluded.invoice_date,
            terms_days = excluded.terms_days,
            po_number = excluded.po_number,
            notes = excluded.notes,
            pdf_file_name = excluded.pdf_file_name,
            issued_at = excluded.issued_at,
            updated_at = excluded.updated_at
        """,
        [
            (
                row["id"],
                row["invoice_number"],
                row["project_id"],
                row["customer_id"],
                row["invoice_date"],
                row["terms_days"],
                row["po_number"],
                row["notes"],
                row["pdf_file_name"],
                row["issued_at"],
                row["updated_at"],
                row["updated_at"],
            )
            for row in INVOICE_SEED_DATA
        ],
    )

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
        ON CONFLICT(id) DO NOTHING
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
            for row in SUPPORTING_INVOICE_TIME_ENTRY_SEED_DATA
        ],
    )

    connection.executemany(
        """
        INSERT INTO payments (
            id,
            customer_id,
            payment_date,
            payment_type,
            reference_number,
            amount_cents,
            notes,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO NOTHING
        """,
        [
            (
                row["id"],
                row["customer_id"],
                row["payment_date"],
                row["payment_type"],
                row["reference_number"],
                row["amount_cents"],
                row["notes"],
                row["updated_at"],
                row["updated_at"],
            )
            for row in SUPPORTING_PAYMENT_SEED_DATA
        ],
    )

    connection.executemany(
        """
        INSERT INTO payment_applications (
            id,
            payment_id,
            invoice_id,
            applied_amount_cents,
            applied_at
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO NOTHING
        """,
        [
            (
                row["id"],
                row["payment_id"],
                row["invoice_id"],
                row["applied_amount_cents"],
                row["applied_at"],
            )
            for row in SUPPORTING_PAYMENT_APPLICATION_SEED_DATA
        ],
    )

    connection.executemany(
        "UPDATE time_entries SET invoice_id = ? WHERE id = ?",
        [
            (301, 401),
            (301, 402),
            (201, 403),
            (188, 406),
            (None, 407),
        ],
    )
    connection.executemany(
        "UPDATE expenses SET invoice_id = ? WHERE id = ?",
        [
            (301, 812),
            (205, 813),
            (None, 815),
            (188, 816),
            (None, 817),
        ],
    )
    connection.commit()
    return len(INVOICE_SEED_DATA)
