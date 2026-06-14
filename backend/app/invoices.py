from __future__ import annotations

from datetime import timedelta
from html import escape
from pathlib import Path
import re
import sqlite3

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .company import fetch_company_profile
from .date_utils import parse_iso_date, utc_now, validate_iso_date
from .expenses import expense_select_sql
from .projects import project_lookup
from .time_entries import time_entry_select_sql


class InvoiceWrite(BaseModel):
    invoice_number: str | None = None
    project_id: int
    invoice_date: str
    terms_days: int
    po_number: str | None = None
    notes: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("project_id")
    @classmethod
    def positive_project_id(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Project is required.")
        return value

    @field_validator("terms_days")
    @classmethod
    def non_negative_terms_days(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Terms must be zero or greater.")
        return value

    @field_validator("invoice_date")
    @classmethod
    def valid_invoice_date(cls, value: str) -> str:
        return validate_iso_date(value, label="Invoice date")

    @field_validator("invoice_number")
    @classmethod
    def normalize_invoice_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class InvoiceSelectionWrite(BaseModel):
    time_entry_ids: list[int] = Field(default_factory=list)
    expense_ids: list[int] = Field(default_factory=list)


class InvoiceSavePrintInvoiceWrite(InvoiceWrite):
    id: int | None = None


class InvoiceSavePrintWrite(BaseModel):
    invoice: InvoiceSavePrintInvoiceWrite
    time_entry_ids: list[int] = Field(default_factory=list)
    expense_ids: list[int] = Field(default_factory=list)


def currency(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def terms_label(terms_days: int) -> str:
    return "Due on receipt" if terms_days <= 0 else f"Net {terms_days}"


def format_print_date(value: str) -> str:
    return parse_iso_date(value).strftime("%m/%d/%Y")


def format_due_date(invoice_date: str, terms_days: int) -> str:
    due_date = parse_iso_date(invoice_date) + timedelta(days=max(terms_days, 0))
    return due_date.strftime("%m/%d/%Y")


def invoice_terms_notice(terms_days: int) -> str:
    if terms_days <= 0:
        return "Payment due on receipt. Overdue accounts subject to a service charge of 1% per month."
    return f"Total due in {terms_days} days. Overdue accounts subject to a service charge of 1% per month."


def project_reference(invoice: dict[str, object]) -> str:
    description = str(invoice.get("project_description") or "").strip()
    project_number = str(invoice["project_number"])
    return f"{project_number} - {description}" if description else project_number


def html_line_breaks(lines: list[str]) -> str:
    return "<br>".join(escape(line) for line in lines if line)


def render_invoice_table_rows(payload: dict[str, object]) -> str:
    selected_time_entries = payload["selected_time_entries"]
    selected_expenses = payload["selected_expenses"]
    rows: list[str] = []

    if selected_time_entries:
        rows.append(
            '<tr class="section-row"><td colspan="6">Services</td></tr>'
        )
        for entry in selected_time_entries:
            quantity = int(entry["minutes"]) / 60
            rows.append(
                """
                <tr>
                    <td>{date}</td>
                    <td>{category}</td>
                    <td>{description}</td>
                    <td class="numeric">{quantity:.2f}</td>
                    <td class="numeric">{unit_price}</td>
                    <td class="numeric">{line_total}</td>
                </tr>
                """.format(
                    date=escape(format_print_date(str(entry["entry_date"]))),
                    category=escape(str(entry["rate_code"])),
                    description=escape(str(entry["description"])),
                    quantity=quantity,
                    unit_price=escape(currency(int(entry["rate_cents"]))),
                    line_total=escape(currency(int(entry["line_total_cents"]))),
                ).strip()
            )
        rows.append(
            """
            <tr class="subtotal-row">
                <td colspan="5">Sub-Total Service</td>
                <td class="numeric">{subtotal}</td>
            </tr>
            """.format(subtotal=escape(currency(int(payload["summary"]["time_total_cents"]))))
        )

    if selected_expenses:
        rows.append(
            '<tr class="section-row"><td colspan="6">Expenses</td></tr>'
        )
        for expense in selected_expenses:
            description = " - ".join(part for part in [str(expense["vendor"]), str(expense["description"])] if part and part != "None")
            rows.append(
                """
                <tr>
                    <td>{date}</td>
                    <td>{category}</td>
                    <td>{description}</td>
                    <td class="numeric">1.00</td>
                    <td class="numeric">{unit_price}</td>
                    <td class="numeric">{line_total}</td>
                </tr>
                """.format(
                    date=escape(format_print_date(str(expense["entry_date"]))),
                    category=escape(str(expense["category"])),
                    description=escape(description),
                    unit_price=escape(currency(int(expense["line_total_cents"]))),
                    line_total=escape(currency(int(expense["line_total_cents"]))),
                ).strip()
            )
        rows.append(
            """
            <tr class="subtotal-row">
                <td colspan="5">Sub-Total Expenses</td>
                <td class="numeric">{subtotal}</td>
            </tr>
            """.format(subtotal=escape(currency(int(payload["summary"]["expense_total_cents"]))))
        )

    if not rows:
        rows.append('<tr><td colspan="6" class="empty-row">No billable items selected.</td></tr>')

    return "\n".join(rows)


def build_invoice_print_html(payload: dict[str, object], company_profile: dict[str, object]) -> str:
    invoice = payload["invoice"]
    summary = payload["summary"]
    customer_lines = [
        str(invoice["customer_name"]),
        str(invoice["street_address"]),
        f"{invoice['city']}, {invoice['state']} {invoice['zip']}",
        f"Phone: {invoice['phone']}",
        f"Email: {invoice['email']}",
    ]
    company_address_lines = [
        str(company_profile["street_address"]),
        f"{company_profile['city']}, {company_profile['state']} {company_profile['zip']}",
    ]
    company_contact_lines = [
        f"Email: {company_profile['email']}",
        f"Phone: {company_profile['phone']}",
    ]
    notes_block = ""
    if invoice.get("notes"):
        notes_block = """
        <section class="notes-card">
            <h3>Notes</h3>
            <p>{notes}</p>
        </section>
        """.format(notes=escape(str(invoice["notes"])))

    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Invoice {invoice_number}</title>
    <style>
        :root {{
            color-scheme: light;
            --paper: #ffffff;
            --ink: #1f2933;
            --muted: #5f6c7b;
            --border: #d6d9de;
            --accent: #214f7a;
            --accent-soft: #eaf1f7;
            --surface: #eef2f5;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            background: var(--surface);
            color: var(--ink);
            font-family: "Segoe UI", Arial, sans-serif;
            line-height: 1.35;
        }}
        .toolbar {{
            position: sticky;
            top: 0;
            display: flex;
            justify-content: flex-end;
            gap: 12px;
            padding: 16px 24px;
            background: rgba(238, 242, 245, 0.96);
            border-bottom: 1px solid var(--border);
        }}
        .toolbar button {{
            border: 1px solid var(--accent);
            background: var(--accent);
            color: #fff;
            border-radius: 999px;
            padding: 10px 18px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
        }}
        .page {{
            width: 8.5in;
            min-height: 11in;
            margin: 24px auto;
            padding: 0.65in;
            background: var(--paper);
            box-shadow: 0 12px 40px rgba(31, 41, 51, 0.12);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 28px;
            margin-bottom: 28px;
        }}
        .company-block h1 {{
            margin: 0 0 8px;
            font-size: 30px;
            letter-spacing: 0.02em;
        }}
        .company-block p,
        .meta-card p,
        .bill-card p,
        .summary-table td,
        .notes-card p,
        .footer p {{
            margin: 0;
        }}
        .company-block .detail {{
            color: var(--muted);
            font-size: 14px;
        }}
        .invoice-heading {{ text-align: right; }}
        .invoice-heading h2 {{
            margin: 0 0 10px;
            font-size: 34px;
            color: var(--accent);
            letter-spacing: 0.08em;
        }}
        .invoice-number {{
            font-size: 16px;
            font-weight: 700;
        }}
        .top-grid {{
            display: grid;
            grid-template-columns: 1.25fr 0.95fr;
            gap: 20px;
            margin-bottom: 28px;
        }}
        .bill-card,
        .meta-card,
        .notes-card {{
            border: 1px solid var(--border);
            background: #fff;
        }}
        .bill-card {{ padding: 18px 20px; }}
        .bill-card h3,
        .notes-card h3 {{
            margin: 0 0 12px;
            font-size: 12px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--muted);
        }}
        .bill-card .name {{
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        .bill-card .detail {{ color: var(--muted); font-size: 14px; }}
        .meta-card {{ padding: 10px 16px; }}
        .meta-row {{
            display: flex;
            justify-content: space-between;
            gap: 16px;
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}
        .meta-row:last-child {{ border-bottom: none; }}
        .meta-label {{
            color: var(--muted);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 11px;
        }}
        .meta-value {{ text-align: right; font-weight: 600; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 24px;
        }}
        thead th {{
            padding: 12px 10px;
            background: var(--accent-soft);
            border-top: 2px solid var(--accent);
            border-bottom: 1px solid var(--border);
            text-align: left;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 11px;
            color: var(--muted);
        }}
        tbody td {{
            padding: 11px 10px;
            border-bottom: 1px solid var(--border);
            vertical-align: top;
            font-size: 14px;
        }}
        .numeric {{ text-align: right; white-space: nowrap; }}
        .section-row td {{
            background: #f8fafc;
            color: var(--accent);
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 11px;
        }}
        .subtotal-row td {{ font-weight: 700; background: #fcfcfd; }}
        .empty-row {{ text-align: center; color: var(--muted); }}
        .summary-wrap {{
            display: flex;
            justify-content: flex-end;
            margin-bottom: 22px;
        }}
        .summary-table {{ width: 320px; }}
        .summary-table td {{
            padding: 9px 12px;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}
        .summary-table tr:last-child td {{
            border-top: 2px solid var(--accent);
            border-bottom: none;
            font-size: 18px;
            font-weight: 800;
            color: var(--accent);
        }}
        .notes-card {{ margin: 0 0 18px; padding: 18px 20px; }}
        .footer {{
            margin-top: 28px;
            padding-top: 16px;
            border-top: 1px solid var(--border);
            color: var(--muted);
            font-size: 13px;
        }}
        .footer p + p {{ margin-top: 6px; }}
        @page {{ size: letter; margin: 0.45in; }}
        @media print {{
            body {{ background: #fff; }}
            .toolbar {{ display: none; }}
            .page {{
                margin: 0;
                width: auto;
                min-height: auto;
                box-shadow: none;
                padding: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="toolbar">
        <button type="button" onclick="window.print()">Print Invoice</button>
    </div>
    <main class="page">
        <header class="header">
            <div class="company-block">
                <h1>{company_name}</h1>
                <p class="detail">{company_address}</p>
                <p class="detail" style="margin-top: 10px;">{company_contact}</p>
            </div>
            <div class="invoice-heading">
                <h2>INVOICE</h2>
                <p class="invoice-number">Invoice #: {invoice_number}</p>
            </div>
        </header>
        <section class="top-grid">
            <div class="bill-card">
                <h3>Bill To</h3>
                <p class="name">{customer_name}</p>
                <p class="detail">{customer_block}</p>
            </div>
            <div class="meta-card">
                <div class="meta-row"><span class="meta-label">Invoice Date</span><span class="meta-value">{invoice_date}</span></div>
                <div class="meta-row"><span class="meta-label">Due Date</span><span class="meta-value">{due_date}</span></div>
                <div class="meta-row"><span class="meta-label">Terms</span><span class="meta-value">{terms}</span></div>
                <div class="meta-row"><span class="meta-label">Project</span><span class="meta-value">{project_number}</span></div>
            </div>
        </section>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Category</th>
                    <th>Description</th>
                    <th class="numeric">Qty</th>
                    <th class="numeric">Unit Price</th>
                    <th class="numeric">Price</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        <div class="summary-wrap">
            <table class="summary-table">
                <tbody>
                    <tr><td>Sub-Total Invoice</td><td class="numeric">{invoice_total}</td></tr>
                    <tr><td>Prior Balance</td><td class="numeric">{prior_balance}</td></tr>
                    <tr><td>Unapplied Credit</td><td class="numeric">{unapplied_credit}</td></tr>
                    <tr><td>Total Due</td><td class="numeric">{open_balance}</td></tr>
                </tbody>
            </table>
        </div>
        {notes_block}
        <footer class="footer">
            <p>{terms_notice}</p>
            <p>Make all checks payable to {company_name}</p>
        </footer>
    </main>
</body>
</html>
""".format(
        company_name=escape(str(company_profile["company_name"])),
        company_address=html_line_breaks(company_address_lines),
        company_contact=html_line_breaks(company_contact_lines),
        invoice_number=escape(str(invoice["invoice_number"])),
        customer_name=escape(str(invoice["customer_name"])),
        customer_block=html_line_breaks(customer_lines[1:]),
        invoice_date=escape(format_print_date(str(invoice["invoice_date"]))),
        due_date=escape(str(invoice["due_date"])),
        terms=escape(terms_label(int(invoice["terms_days"]))),
        project_number=escape(project_reference(invoice)),
        table_rows=render_invoice_table_rows(payload),
        invoice_total=escape(currency(int(summary["invoice_total_cents"]))),
        prior_balance=escape(currency(int(summary["prior_balance_cents"]))),
        unapplied_credit=escape(currency(int(summary["unapplied_credit_cents"]))),
        open_balance=escape(currency(int(summary["open_balance_after_issue_cents"]))),
        notes_block=notes_block,
        terms_notice=escape(invoice_terms_notice(int(invoice["terms_days"]))),
    )


def next_invoice_number(connection: sqlite3.Connection, invoice_date: str) -> str:
    year = parse_iso_date(invoice_date).year
    rows = connection.execute("SELECT invoice_number FROM invoices WHERE invoice_number LIKE ?", (f"INV-{year}-%",)).fetchall()
    suffixes = []
    for row in rows:
        parts = str(row["invoice_number"] or "").split("-")
        if len(parts) >= 3 and parts[-1].isdigit():
            suffixes.append(int(parts[-1]))
    next_suffix = (max(suffixes) if suffixes else 0) + 1
    return f"INV-{year}-{str(next_suffix).zfill(3)}"


def invoice_select_sql() -> str:
    return """
    SELECT
        i.id,
        i.invoice_number,
        i.project_id,
        p.project_number,
        p.description AS project_description,
        i.customer_id,
        c.customer_name,
        c.street_address,
        c.city,
        c.state,
        c.zip,
        c.contact_name,
        c.email,
        c.phone,
        i.invoice_date,
        i.terms_days,
        i.po_number,
        i.notes,
        i.pdf_file_name,
        i.issued_at,
        i.updated_at,
        COALESCE(ibv.time_amount_cents, 0) AS time_amount_cents,
        COALESCE(ibv.expense_amount_cents, 0) AS expense_amount_cents,
        COALESCE(ibv.paid_amount_cents, 0) AS paid_amount_cents,
        COALESCE(ibv.invoice_amount_cents, 0) AS invoice_amount_cents,
        COALESCE(ibv.open_amount_cents, 0) AS open_amount_cents,
        COALESCE(cbv.unapplied_credit_cents, 0) AS unapplied_credit_cents
    FROM invoices i
    JOIN projects p ON p.id = i.project_id
    JOIN customers c ON c.id = i.customer_id
    LEFT JOIN invoice_balance_view ibv ON ibv.invoice_id = i.id
    LEFT JOIN customer_balance_view cbv ON cbv.customer_id = i.customer_id
    """


def prior_balance_cents(connection: sqlite3.Connection, customer_id: int, invoice_id: int) -> int:
    row = connection.execute(
        """
        SELECT COALESCE(SUM(ibv.open_amount_cents), 0) AS prior_balance_cents
        FROM invoice_balance_view ibv
        JOIN invoices i ON i.id = ibv.invoice_id
        WHERE i.customer_id = ? AND i.id != ? AND i.issued_at IS NOT NULL
        """,
        (customer_id, invoice_id),
    ).fetchone()
    return int(row["prior_balance_cents"] if row is not None else 0)


def derive_invoice_status(invoice: dict[str, object]) -> str:
    if not invoice["issued_at"]:
        return "draft"
    if int(invoice["invoice_amount_cents"] or 0) > 0 and int(invoice["open_balance_cents"] or 0) <= 0:
        return "paid"
    return "printed"


def row_to_invoice(connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, object]:
    due_date = format_due_date(str(row["invoice_date"]), int(row["terms_days"]))
    invoice = {
        "id": row["id"],
        "invoice_number": row["invoice_number"],
        "project_id": row["project_id"],
        "project_number": row["project_number"],
        "project_description": row["project_description"],
        "customer_id": row["customer_id"],
        "customer_name": row["customer_name"],
        "street_address": row["street_address"],
        "city": row["city"],
        "state": row["state"],
        "zip": row["zip"],
        "contact_name": row["contact_name"],
        "email": row["email"],
        "phone": row["phone"],
        "invoice_date": row["invoice_date"],
        "due_date": due_date,
        "terms_days": row["terms_days"],
        "po_number": row["po_number"],
        "notes": row["notes"],
        "pdf_file_name": row["pdf_file_name"],
        "issued_at": row["issued_at"],
        "paid_amount_cents": row["paid_amount_cents"],
        "invoice_amount_cents": row["invoice_amount_cents"],
        "open_balance_cents": max(0, int(row["open_amount_cents"])),
        "prior_balance_cents": prior_balance_cents(connection, row["customer_id"], row["id"]),
        "unapplied_credit_cents": row["unapplied_credit_cents"],
        "updated_at": row["updated_at"],
    }
    invoice["status"] = derive_invoice_status(invoice)
    return invoice


def fetch_invoices(connection: sqlite3.Connection, year: str | None = None) -> list[dict[str, object]]:
    sql = invoice_select_sql()
    parameters: list[object] = []
    if year:
        sql += " WHERE substr(i.invoice_date, 1, 4) = ?"
        parameters.append(year)
    sql += " ORDER BY i.invoice_date DESC, i.id DESC"
    rows = connection.execute(sql, parameters).fetchall()
    return [row_to_invoice(connection, row) for row in rows]


def fetch_invoice(connection: sqlite3.Connection, invoice_id: int) -> dict[str, object] | None:
    row = connection.execute(invoice_select_sql() + " WHERE i.id = ?", (invoice_id,)).fetchone()
    if row is None:
        return None
    return row_to_invoice(connection, row)


def fetch_selected_time_entries(connection: sqlite3.Connection, invoice_id: int) -> list[dict[str, object]]:
    rows = connection.execute(
        time_entry_select_sql() + " WHERE te.invoice_id = ? ORDER BY te.entry_date, te.id",
        (invoice_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_selected_expenses(connection: sqlite3.Connection, invoice_id: int) -> list[dict[str, object]]:
    rows = connection.execute(
        expense_select_sql() + " WHERE e.invoice_id = ? ORDER BY e.entry_date, e.id",
        (invoice_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_eligible_time_entries(connection: sqlite3.Connection, invoice: dict[str, object]) -> list[dict[str, object]]:
    rows = connection.execute(
        time_entry_select_sql()
        + " WHERE te.project_id = ? AND te.rate_cents > 0 AND (te.invoice_id IS NULL OR te.invoice_id = ?) ORDER BY te.entry_date, te.id",
        (invoice["project_id"], invoice["id"]),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_eligible_expenses(connection: sqlite3.Connection, invoice: dict[str, object]) -> list[dict[str, object]]:
    rows = connection.execute(
        expense_select_sql()
        + " WHERE e.project_id = ? AND e.is_billable = 1 AND (e.invoice_id IS NULL OR e.invoice_id = ?) ORDER BY e.entry_date, e.id",
        (invoice["project_id"], invoice["id"]),
    ).fetchall()
    return [dict(row) for row in rows]


def invoice_editor_payload(connection: sqlite3.Connection, invoice_id: int) -> dict[str, object] | None:
    invoice = fetch_invoice(connection, invoice_id)
    if invoice is None:
        return None
    selected_time_entries = fetch_selected_time_entries(connection, invoice_id)
    selected_expenses = fetch_selected_expenses(connection, invoice_id)
    eligible_time_entries = fetch_eligible_time_entries(connection, invoice)
    eligible_expenses = fetch_eligible_expenses(connection, invoice)
    summary = {
        "time_total_cents": sum(entry["line_total_cents"] for entry in selected_time_entries),
        "expense_total_cents": sum(expense["line_total_cents"] for expense in selected_expenses),
        "invoice_total_cents": invoice["invoice_amount_cents"],
        "prior_balance_cents": invoice["prior_balance_cents"],
        "unapplied_credit_cents": invoice["unapplied_credit_cents"],
        "open_balance_after_issue_cents": max(
            0,
            int(invoice["prior_balance_cents"]) + int(invoice["invoice_amount_cents"]) - int(invoice["unapplied_credit_cents"]),
        ),
    }
    return {
        "invoice": invoice,
        "selected_time_entries": selected_time_entries,
        "selected_expenses": selected_expenses,
        "eligible_time_entries": eligible_time_entries,
        "eligible_expenses": eligible_expenses,
        "summary": summary,
    }


def invoice_new_editor_payload(
    connection: sqlite3.Connection,
    *,
    project_id: int,
    invoice_date: str,
    terms_days: int = 30,
) -> dict[str, object] | None:
    project = connection.execute(
        """
        SELECT
            p.id AS project_id,
            p.project_number,
            p.description AS project_description,
            c.id AS customer_id,
            c.customer_name,
            c.street_address,
            c.city,
            c.state,
            c.zip,
            c.contact_name,
            c.email,
            c.phone
        FROM projects p
        JOIN customers c ON c.id = p.customer_id
        WHERE p.id = ?
        """,
        (project_id,),
    ).fetchone()
    if project is None:
        return None

    invoice_date = validate_iso_date(invoice_date, label="Invoice date")
    invoice = {
        "id": None,
        "invoice_number": next_invoice_number(connection, invoice_date),
        "project_id": project["project_id"],
        "project_number": project["project_number"],
        "project_description": project["project_description"],
        "customer_id": project["customer_id"],
        "customer_name": project["customer_name"],
        "street_address": project["street_address"],
        "city": project["city"],
        "state": project["state"],
        "zip": project["zip"],
        "contact_name": project["contact_name"],
        "email": project["email"],
        "phone": project["phone"],
        "invoice_date": invoice_date,
        "due_date": format_due_date(invoice_date, terms_days),
        "terms_days": terms_days,
        "po_number": None,
        "notes": "Thank you for your business.",
        "pdf_file_name": None,
        "issued_at": None,
        "paid_amount_cents": 0,
        "invoice_amount_cents": 0,
        "open_balance_cents": 0,
        "prior_balance_cents": prior_balance_cents(connection, project["customer_id"], 0),
        "unapplied_credit_cents": 0,
        "updated_at": utc_now(),
        "status": "new",
    }
    eligible_time_entries = fetch_eligible_time_entries(connection, invoice)
    eligible_expenses = fetch_eligible_expenses(connection, invoice)
    return {
        "invoice": invoice,
        "selected_time_entries": [],
        "selected_expenses": [],
        "eligible_time_entries": eligible_time_entries,
        "eligible_expenses": eligible_expenses,
        "summary": {
            "time_total_cents": 0,
            "expense_total_cents": 0,
            "invoice_total_cents": 0,
            "prior_balance_cents": invoice["prior_balance_cents"],
            "unapplied_credit_cents": 0,
            "open_balance_after_issue_cents": int(invoice["prior_balance_cents"]),
        },
    }


def invoice_bootstrap_payload(connection: sqlite3.Connection, year: str | None = None) -> dict[str, object]:
    invoices = fetch_invoices(connection, year=year)
    status_counts = {"all": len(invoices), "draft": 0, "printed": 0, "paid": 0}
    for invoice in invoices:
        status_counts[invoice["status"]] += 1
    return {
        "invoices": invoices,
        "projects": project_lookup(connection),
        "status_counts": status_counts,
    }


def resolve_project(connection: sqlite3.Connection, project_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id, project_number, customer_id FROM projects WHERE id = ?",
        (project_id,),
    ).fetchone()


def clear_invoice_selection(connection: sqlite3.Connection, invoice_id: int) -> None:
    connection.execute("UPDATE time_entries SET invoice_id = NULL WHERE invoice_id = ?", (invoice_id,))
    connection.execute("UPDATE expenses SET invoice_id = NULL WHERE invoice_id = ?", (invoice_id,))


def validate_selection_rows(
    connection: sqlite3.Connection,
    invoice: dict[str, object],
    time_entry_ids: list[int],
    expense_ids: list[int],
) -> None:
    if time_entry_ids:
        placeholders = ", ".join("?" for _ in time_entry_ids)
        rows = connection.execute(
            f"SELECT id, project_id, invoice_id, rate_cents FROM time_entries WHERE id IN ({placeholders})",
            time_entry_ids,
        ).fetchall()
        if len(rows) != len(set(time_entry_ids)):
            raise ValueError("One or more time entries were not found.")
        for row in rows:
            if row["project_id"] != invoice["project_id"] or row["rate_cents"] <= 0:
                raise ValueError("Time entry selection is not eligible for this invoice.")
            if row["invoice_id"] not in (None, invoice["id"]):
                raise ValueError("A selected time entry is already assigned to another invoice.")
    if expense_ids:
        placeholders = ", ".join("?" for _ in expense_ids)
        rows = connection.execute(
            f"SELECT id, project_id, invoice_id, is_billable FROM expenses WHERE id IN ({placeholders})",
            expense_ids,
        ).fetchall()
        if len(rows) != len(set(expense_ids)):
            raise ValueError("One or more expenses were not found.")
        for row in rows:
            if row["project_id"] != invoice["project_id"] or not row["is_billable"]:
                raise ValueError("Expense selection is not eligible for this invoice.")
            if row["invoice_id"] not in (None, invoice["id"]):
                raise ValueError("A selected expense is already assigned to another invoice.")


def stored_invoice_file_name(invoice_id: int, invoice_number: str) -> str:
    safe_number = re.sub(r"[^A-Za-z0-9._-]+", "-", invoice_number).strip("-._")
    safe_number = safe_number or "invoice"
    return f"invoice-{invoice_id}-{safe_number}.html"


def ensure_invoice_output_dir(data_dir: Path) -> Path:
    output_dir = data_dir / "invoices"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def create_invoice_without_commit(connection: sqlite3.Connection, payload: InvoiceWrite) -> int:
    project = resolve_project(connection, payload.project_id)
    if project is None:
        raise ValueError("Project not found.")

    timestamp = utc_now()
    invoice_number = payload.invoice_number or next_invoice_number(connection, payload.invoice_date)
    cursor = connection.execute(
        """
        INSERT INTO invoices (
            invoice_number,
            project_id,
            customer_id,
            invoice_date,
            terms_days,
            po_number,
            notes,
            issued_at,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invoice_number,
            payload.project_id,
            project["customer_id"],
            payload.invoice_date,
            payload.terms_days,
            payload.po_number,
            payload.notes,
            None,
            timestamp,
            timestamp,
        ),
    )
    return int(cursor.lastrowid)


def update_invoice_without_commit(
    connection: sqlite3.Connection,
    invoice_id: int,
    payload: InvoiceWrite,
) -> bool:
    existing = fetch_invoice(connection, invoice_id)
    if existing is None:
        return False

    project = resolve_project(connection, payload.project_id)
    if project is None:
        raise ValueError("Project not found.")

    connection.execute(
        """
        UPDATE invoices
        SET
            invoice_number = ?,
            project_id = ?,
            customer_id = ?,
            invoice_date = ?,
            terms_days = ?,
            po_number = ?,
            notes = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            payload.invoice_number or existing["invoice_number"],
            payload.project_id,
            project["customer_id"],
            payload.invoice_date,
            payload.terms_days,
            payload.po_number,
            payload.notes,
            utc_now(),
            invoice_id,
        ),
    )
    return True


def replace_invoice_selection_without_commit(
    connection: sqlite3.Connection,
    invoice_id: int,
    payload: InvoiceSelectionWrite,
) -> None:
    invoice = fetch_invoice(connection, invoice_id)
    if invoice is None:
        raise ValueError("Invoice not found.")

    time_entry_ids = list(dict.fromkeys(payload.time_entry_ids))
    expense_ids = list(dict.fromkeys(payload.expense_ids))
    if not time_entry_ids and not expense_ids:
        raise ValueError("Select at least one billable row before saving the invoice.")

    validate_selection_rows(connection, invoice, time_entry_ids, expense_ids)
    clear_invoice_selection(connection, invoice_id)

    if time_entry_ids:
        connection.execute(
            f"UPDATE time_entries SET invoice_id = ? WHERE id IN ({', '.join('?' for _ in time_entry_ids)})",
            (invoice_id, *time_entry_ids),
        )
    if expense_ids:
        connection.execute(
            f"UPDATE expenses SET invoice_id = ? WHERE id IN ({', '.join('?' for _ in expense_ids)})",
            (invoice_id, *expense_ids),
        )


def save_invoice_html_without_commit(
    connection: sqlite3.Connection,
    invoice_id: int,
    data_dir: Path,
) -> tuple[dict[str, object], dict[str, object], Path]:
    invoice = fetch_invoice(connection, invoice_id)
    if invoice is None:
        raise ValueError("Invoice not found.")

    timestamp = utc_now()
    if not invoice["issued_at"]:
        connection.execute(
            "UPDATE invoices SET issued_at = ?, updated_at = ? WHERE id = ?",
            (timestamp, timestamp, invoice_id),
        )

    payload = invoice_editor_payload(connection, invoice_id)
    if payload is None:
        raise ValueError("Invoice not found.")

    invoice = payload["invoice"]
    if int(invoice["invoice_amount_cents"]) <= 0:
        raise ValueError("Select at least one billable row before saving the invoice.")

    company_profile = fetch_company_profile(connection)
    document_html = build_invoice_print_html(payload, company_profile)
    output_dir = ensure_invoice_output_dir(data_dir)
    file_name = stored_invoice_file_name(int(invoice["id"]), str(invoice["invoice_number"]))
    file_path = output_dir / file_name
    relative_path = f"invoices/{file_name}"

    previous_path = invoice.get("pdf_file_name")
    if previous_path and previous_path != relative_path:
        old_file_path = data_dir / str(previous_path)
        if old_file_path.exists() and old_file_path.is_file():
            old_file_path.unlink()

    file_path.write_text(document_html, encoding="utf-8")
    connection.execute(
        "UPDATE invoices SET pdf_file_name = ?, updated_at = ? WHERE id = ?",
        (relative_path, utc_now(), invoice_id),
    )

    refreshed_payload = invoice_editor_payload(connection, invoice_id)
    if refreshed_payload is None:
        raise ValueError("Invoice not found.")
    return refreshed_payload["invoice"], refreshed_payload, file_path


def save_print_invoice(
    connection: sqlite3.Connection,
    payload: InvoiceSavePrintWrite,
    data_dir: Path,
) -> dict[str, object] | None:
    invoice_payload = InvoiceWrite(**payload.invoice.model_dump(exclude={"id"}))
    invoice_id = payload.invoice.id
    if invoice_id is None:
        invoice_id = create_invoice_without_commit(connection, invoice_payload)
    else:
        updated = update_invoice_without_commit(connection, invoice_id, invoice_payload)
        if not updated:
            return None

    replace_invoice_selection_without_commit(
        connection,
        invoice_id,
        InvoiceSelectionWrite(
            time_entry_ids=payload.time_entry_ids,
            expense_ids=payload.expense_ids,
        ),
    )
    invoice, editor_payload, _file_path = save_invoice_html_without_commit(connection, invoice_id, data_dir)
    connection.commit()
    return {
        "invoice": invoice,
        "editor": editor_payload,
        "printable_url": f"/api/invoices/{invoice_id}/document",
    }


def fetch_saved_invoice_document(
    connection: sqlite3.Connection,
    invoice_id: int,
    data_dir: Path,
) -> str | None:
    invoice = fetch_invoice(connection, invoice_id)
    if invoice is None:
        return None
    saved_path = invoice.get("pdf_file_name")
    if not saved_path:
        return None
    file_path = data_dir / str(saved_path)
    try:
        resolved_file = file_path.resolve()
        resolved_data_dir = data_dir.resolve()
    except OSError:
        return None
    if resolved_data_dir not in resolved_file.parents:
        return None
    if not resolved_file.exists() or not resolved_file.is_file():
        return None
    return resolved_file.read_text(encoding="utf-8")
