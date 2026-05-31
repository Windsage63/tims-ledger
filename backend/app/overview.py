from __future__ import annotations

import sqlite3


def scalar(connection: sqlite3.Connection, query: str, parameters: tuple[object, ...] = ()) -> int:
    row = connection.execute(query, parameters).fetchone()
    if row is None:
        return 0
    return int(row[0] or 0)


def overview_bootstrap_payload(connection: sqlite3.Connection) -> dict[str, object]:
    customers_count = scalar(connection, "SELECT COUNT(*) FROM customers")
    projects_count = scalar(connection, "SELECT COUNT(*) FROM projects")
    time_entries_count = scalar(connection, "SELECT COUNT(*) FROM time_entries")
    expenses_count = scalar(connection, "SELECT COUNT(*) FROM expenses")
    invoices_count = scalar(connection, "SELECT COUNT(*) FROM invoices")
    issued_invoices_count = scalar(connection, "SELECT COUNT(*) FROM invoices WHERE issued_at IS NOT NULL")
    draft_invoices_count = scalar(connection, "SELECT COUNT(*) FROM invoices WHERE issued_at IS NULL")
    payments_count = scalar(connection, "SELECT COUNT(*) FROM payments")

    open_receivables_cents = scalar(
        connection,
        """
        SELECT COALESCE(SUM(ibv.open_amount_cents), 0)
        FROM invoice_balance_view ibv
        JOIN invoices i ON i.id = ibv.invoice_id
        WHERE i.issued_at IS NOT NULL
        """,
    )
    unapplied_receipts_cents = scalar(
        connection,
        "SELECT COALESCE(SUM(unapplied_amount_cents), 0) FROM payment_unapplied_view",
    )
    unbilled_time_cents = scalar(
        connection,
        "SELECT COALESCE(SUM(line_total_cents), 0) FROM unbilled_time_view",
    )
    unbilled_expenses_cents = scalar(
        connection,
        "SELECT COALESCE(SUM(line_total_cents), 0) FROM unbilled_expenses_view",
    )

    return {
        "summary": {
            "customers_count": customers_count,
            "projects_count": projects_count,
            "time_entries_count": time_entries_count,
            "expenses_count": expenses_count,
            "invoices_count": invoices_count,
            "issued_invoices_count": issued_invoices_count,
            "draft_invoices_count": draft_invoices_count,
            "payments_count": payments_count,
            "open_receivables_cents": open_receivables_cents,
            "unapplied_receipts_cents": unapplied_receipts_cents,
            "unbilled_time_cents": unbilled_time_cents,
            "unbilled_expenses_cents": unbilled_expenses_cents,
            "unbilled_work_cents": unbilled_time_cents + unbilled_expenses_cents,
        }
    }