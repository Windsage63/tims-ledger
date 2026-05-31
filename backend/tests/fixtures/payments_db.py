from __future__ import annotations

import sqlite3

from .data import (
    PAYMENT_APPLICATION_SEED_DATA,
    PAYMENT_SEED_DATA,
    SUPPORTING_PAYMENT_EXPENSE_SEED_DATA,
    SUPPORTING_PAYMENT_INVOICE_SEED_DATA,
)

from .invoices_db import load_invoices_db


def load_payments_db(connection: sqlite3.Connection) -> int:
    already_seeded = connection.execute("SELECT 1 FROM payments WHERE id = 75").fetchone()
    if already_seeded is not None:
        return 0

    load_invoices_db(connection)

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
            for row in SUPPORTING_PAYMENT_INVOICE_SEED_DATA
        ],
    )

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
        ON CONFLICT(id) DO UPDATE SET
            entry_date = excluded.entry_date,
            project_id = excluded.project_id,
            customer_id = excluded.customer_id,
            vendor = excluded.vendor,
            description = excluded.description,
            quantity = excluded.quantity,
            unit_cost_cents = excluded.unit_cost_cents,
            line_total_cents = excluded.line_total_cents,
            category = excluded.category,
            is_billable = excluded.is_billable,
            invoice_id = excluded.invoice_id,
            updated_at = excluded.updated_at
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
            for row in SUPPORTING_PAYMENT_EXPENSE_SEED_DATA
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
        ON CONFLICT(id) DO UPDATE SET
            customer_id = excluded.customer_id,
            payment_date = excluded.payment_date,
            payment_type = excluded.payment_type,
            reference_number = excluded.reference_number,
            amount_cents = excluded.amount_cents,
            notes = excluded.notes,
            updated_at = excluded.updated_at
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
            for row in PAYMENT_SEED_DATA
        ],
    )

    connection.executemany(
        "DELETE FROM payment_applications WHERE id = ?",
        [(row["id"],) for row in PAYMENT_APPLICATION_SEED_DATA],
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
        """,
        [
            (
                row["id"],
                row["payment_id"],
                row["invoice_id"],
                row["applied_amount_cents"],
                row["applied_at"],
            )
            for row in PAYMENT_APPLICATION_SEED_DATA
        ],
    )
    connection.commit()
    return len(PAYMENT_SEED_DATA)
