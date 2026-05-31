from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sqlite3

from pydantic import BaseModel, ConfigDict, field_validator

from .expenses import expense_select_sql
from .projects import project_lookup
from .time_entries import time_entry_select_sql


INVOICE_SEED_DATA = [
    {
        "id": 301,
        "invoice_number": "INV-2026-023",
        "project_id": 33,
        "customer_id": 12,
        "invoice_date": "2026-05-31",
        "terms_days": 30,
        "po_number": "PO-1182",
        "notes": "Thank you for your business.",
        "pdf_file_name": None,
        "issued_at": None,
        "updated_at": "2026-05-31T15:00:00Z",
    },
    {
        "id": 201,
        "invoice_number": "INV-2026-014",
        "project_id": 34,
        "customer_id": 19,
        "invoice_date": "2026-05-20",
        "terms_days": 31,
        "po_number": None,
        "notes": "Thank you for your business.",
        "pdf_file_name": "inv-2026-014.pdf",
        "issued_at": "2026-05-20T14:12:00Z",
        "updated_at": "2026-05-20T14:12:00Z",
    },
    {
        "id": 205,
        "invoice_number": "INV-2026-019",
        "project_id": 35,
        "customer_id": 24,
        "invoice_date": "2026-05-21",
        "terms_days": 8,
        "po_number": None,
        "notes": "Reimbursable field costs attached.",
        "pdf_file_name": "inv-2026-019.pdf",
        "issued_at": "2026-05-21T11:00:00Z",
        "updated_at": "2026-05-21T11:00:00Z",
    },
    {
        "id": 188,
        "invoice_number": "INV-2025-098",
        "project_id": 37,
        "customer_id": 38,
        "invoice_date": "2025-12-17",
        "terms_days": 30,
        "po_number": "PW-44",
        "notes": "Final meeting materials and site review.",
        "pdf_file_name": "inv-2025-098.pdf",
        "issued_at": "2025-12-17T09:00:00Z",
        "updated_at": "2025-12-17T09:00:00Z",
    },
]


SUPPORTING_INVOICE_TIME_ENTRY_SEED_DATA = [
    {
        "id": 407,
        "entry_date": "2026-05-25",
        "project_id": 34,
        "customer_id": 19,
        "description": "Redline incorporation and sheet set coordination.",
        "minutes": 120,
        "rate_code": "ST",
        "rate_cents": 13800,
        "line_total_cents": 27600,
        "invoice_id": None,
        "updated_at": "2026-05-31T15:00:00Z",
    },
]


SUPPORTING_PAYMENT_SEED_DATA = [
    {
        "id": 68,
        "customer_id": 38,
        "payment_date": "2025-12-30",
        "payment_type": "payment",
        "reference_number": "EFT-188",
        "amount_cents": 78200,
        "notes": "Final payment for meeting materials and site review.",
        "updated_at": "2025-12-30T11:00:00Z",
    },
    {
        "id": 72,
        "customer_id": 19,
        "payment_date": "2026-05-29",
        "payment_type": "payment",
        "reference_number": "ACH-4401",
        "amount_cents": 25000,
        "notes": "Partial ACH receipt.",
        "updated_at": "2026-05-31T15:00:00Z",
    },
]


SUPPORTING_PAYMENT_APPLICATION_SEED_DATA = [
    {
        "id": 890,
        "payment_id": 68,
        "invoice_id": 188,
        "applied_amount_cents": 78200,
        "applied_at": "2025-12-30T11:05:00Z",
    },
    {
        "id": 902,
        "payment_id": 72,
        "invoice_id": 201,
        "applied_amount_cents": 20000,
        "applied_at": "2026-05-29T14:15:00Z",
    },
]


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
        if not value:
            raise ValueError("Invoice date is required.")
        date.fromisoformat(value)
        return value

    @field_validator("invoice_number")
    @classmethod
    def normalize_invoice_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class InvoiceSelectionWrite(BaseModel):
    time_entry_ids: list[int] = []
    expense_ids: list[int] = []


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def derive_due_date(invoice_date: str, terms_days: int) -> str:
    return (parse_iso_date(invoice_date) + timedelta(days=terms_days)).isoformat()


def slugify_invoice_number(invoice_number: str) -> str:
    return invoice_number.lower().replace(" ", "-")


def invoice_pdf_directory(data_dir: Path) -> Path:
    return data_dir / "invoices"


def pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def currency(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def line_for_time_entry(entry: dict[str, object]) -> str:
    return f"{entry['entry_date']}  {entry['rate_code']}  {entry['minutes']} min  {currency(int(entry['line_total_cents']))}  {entry['description']}"


def line_for_expense(expense: dict[str, object]) -> str:
    return f"{expense['entry_date']}  {expense['category']}  {currency(int(expense['line_total_cents']))}  {expense['vendor']} - {expense['description']}"


def build_invoice_pdf_bytes(payload: dict[str, object]) -> bytes:
    invoice = payload["invoice"]
    summary = payload["summary"]
    lines = [
        "Winds Ledger Invoice",
        f"Invoice: {invoice['invoice_number']}",
        f"Customer: {invoice['customer_name']}",
        f"Project: {invoice['project_number']}",
        f"Invoice Date: {invoice['invoice_date']}",
        f"Due Date: {invoice['due_date']}",
        f"PO Number: {invoice['po_number'] or 'None'}",
        "",
        "Time Charges",
    ]

    selected_time_entries = payload["selected_time_entries"]
    selected_expenses = payload["selected_expenses"]
    if selected_time_entries:
        lines.extend(line_for_time_entry(entry)[:110] for entry in selected_time_entries)
    else:
        lines.append("No time charges selected.")

    lines.extend([
        "",
        "Expense Charges",
    ])
    if selected_expenses:
        lines.extend(line_for_expense(expense)[:110] for expense in selected_expenses)
    else:
        lines.append("No expense charges selected.")

    lines.extend([
        "",
        f"Time Total: {currency(int(summary['time_total_cents']))}",
        f"Expense Total: {currency(int(summary['expense_total_cents']))}",
        f"Invoice Total: {currency(int(summary['invoice_total_cents']))}",
        f"Prior Balance: {currency(int(summary['prior_balance_cents']))}",
        f"Unapplied Credit: {currency(int(summary['unapplied_credit_cents']))}",
        f"Open Balance After Issue: {currency(int(summary['open_balance_after_issue_cents']))}",
    ])
    if invoice.get("notes"):
        lines.extend(["", f"Notes: {str(invoice['notes'])[:110]}"])

    content_lines = ["BT", "/F1 11 Tf", "72 780 Td", "14 TL"]
    for index, line in enumerate(lines[:45]):
        escaped = pdf_escape(line)
        if index == 0:
            content_lines.append(f"({escaped}) Tj")
        else:
            content_lines.append(f"T* ({escaped}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(output))
        output.extend(obj)
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)


def write_invoice_pdf(data_dir: Path, payload: dict[str, object]) -> Path:
    invoice = payload["invoice"]
    pdf_dir = invoice_pdf_directory(data_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_file_name = str(invoice["pdf_file_name"] or f"{slugify_invoice_number(str(invoice['invoice_number']))}.pdf")
    pdf_path = pdf_dir / pdf_file_name
    pdf_path.write_bytes(build_invoice_pdf_bytes(payload))
    return pdf_path


def ensure_invoice_seed_data(connection: sqlite3.Connection) -> int:
    already_seeded = connection.execute("SELECT 1 FROM invoices WHERE id = 301").fetchone()
    if already_seeded is not None:
        return 0

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
        i.customer_id,
        c.customer_name,
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
    if str(invoice["due_date"]) < date.today().isoformat():
        return "overdue"
    return "pending"


def row_to_invoice(connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, object]:
    invoice = {
        "id": row["id"],
        "invoice_number": row["invoice_number"],
        "project_id": row["project_id"],
        "project_number": row["project_number"],
        "customer_id": row["customer_id"],
        "customer_name": row["customer_name"],
        "invoice_date": row["invoice_date"],
        "terms_days": row["terms_days"],
        "due_date": derive_due_date(row["invoice_date"], row["terms_days"]),
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


def invoice_summary(connection: sqlite3.Connection, invoice: dict[str, object]) -> dict[str, object]:
    return {
        "time_total_cents": invoice["invoice_amount_cents"] - sum(expense["line_total_cents"] for expense in fetch_selected_expenses(connection, invoice["id"])),
        "expense_total_cents": sum(expense["line_total_cents"] for expense in fetch_selected_expenses(connection, invoice["id"])),
        "invoice_total_cents": invoice["invoice_amount_cents"],
        "prior_balance_cents": invoice["prior_balance_cents"],
        "unapplied_credit_cents": invoice["unapplied_credit_cents"],
        "open_balance_after_issue_cents": max(
            0,
            int(invoice["prior_balance_cents"]) + int(invoice["invoice_amount_cents"]) - int(invoice["unapplied_credit_cents"]),
        ),
    }


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


def invoice_bootstrap_payload(connection: sqlite3.Connection, year: str | None = None) -> dict[str, object]:
    invoices = fetch_invoices(connection, year=year)
    status_counts = {"all": len(invoices), "draft": 0, "pending": 0, "overdue": 0, "paid": 0}
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


def create_invoice(connection: sqlite3.Connection, payload: InvoiceWrite) -> dict[str, object]:
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
            pdf_file_name,
            issued_at,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            None,
            timestamp,
            timestamp,
        ),
    )
    connection.commit()
    invoice = fetch_invoice(connection, cursor.lastrowid)
    if invoice is None:
        raise ValueError("Invoice could not be loaded after creation.")
    return invoice


def clear_invoice_selection(connection: sqlite3.Connection, invoice_id: int) -> None:
    connection.execute("UPDATE time_entries SET invoice_id = NULL WHERE invoice_id = ?", (invoice_id,))
    connection.execute("UPDATE expenses SET invoice_id = NULL WHERE invoice_id = ?", (invoice_id,))


def update_invoice(connection: sqlite3.Connection, invoice_id: int, payload: InvoiceWrite) -> dict[str, object] | None:
    existing = fetch_invoice(connection, invoice_id)
    if existing is None:
        return None
    if existing["issued_at"]:
        raise ValueError("Issued invoices are read-only.")

    project = resolve_project(connection, payload.project_id)
    if project is None:
        raise ValueError("Project not found.")
    if payload.project_id != existing["project_id"]:
        clear_invoice_selection(connection, invoice_id)

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
    connection.commit()
    return fetch_invoice(connection, invoice_id)


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


def replace_invoice_selection(
    connection: sqlite3.Connection,
    invoice_id: int,
    payload: InvoiceSelectionWrite,
) -> dict[str, object] | None:
    invoice = fetch_invoice(connection, invoice_id)
    if invoice is None:
        return None
    if invoice["issued_at"]:
        raise ValueError("Issued invoices are read-only.")

    time_entry_ids = list(dict.fromkeys(payload.time_entry_ids))
    expense_ids = list(dict.fromkeys(payload.expense_ids))
    validate_selection_rows(connection, invoice, time_entry_ids, expense_ids)

    connection.execute(
        f"UPDATE time_entries SET invoice_id = NULL WHERE invoice_id = ? AND id NOT IN ({', '.join('?' for _ in time_entry_ids)})",
        (invoice_id, *time_entry_ids),
    ) if time_entry_ids else connection.execute("UPDATE time_entries SET invoice_id = NULL WHERE invoice_id = ?", (invoice_id,))

    connection.execute(
        f"UPDATE expenses SET invoice_id = NULL WHERE invoice_id = ? AND id NOT IN ({', '.join('?' for _ in expense_ids)})",
        (invoice_id, *expense_ids),
    ) if expense_ids else connection.execute("UPDATE expenses SET invoice_id = NULL WHERE invoice_id = ?", (invoice_id,))

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

    connection.commit()
    return invoice_editor_payload(connection, invoice_id)


def issue_invoice(connection: sqlite3.Connection, invoice_id: int, data_dir: Path) -> dict[str, object] | None:
    invoice = fetch_invoice(connection, invoice_id)
    if invoice is None:
        return None
    if invoice["issued_at"]:
        raise ValueError("Invoice has already been issued.")
    if int(invoice["invoice_amount_cents"]) <= 0:
        raise ValueError("Select at least one billable row before issuing the invoice.")

    pdf_file_name = f"{slugify_invoice_number(str(invoice['invoice_number']))}.pdf"
    connection.execute(
        "UPDATE invoices SET issued_at = ?, pdf_file_name = ?, updated_at = ? WHERE id = ?",
        (utc_now(), pdf_file_name, utc_now(), invoice_id),
    )
    connection.commit()

    payload = invoice_editor_payload(connection, invoice_id)
    if payload is None:
        return None
    pdf_path = write_invoice_pdf(data_dir, payload)
    payload["pdf_reference"] = {
        "file_name": pdf_file_name,
        "download_path": f"/api/invoices/{invoice_id}/pdf",
        "file_path": str(pdf_path),
    }
    return payload


def ensure_invoice_pdf(connection: sqlite3.Connection, invoice_id: int, data_dir: Path) -> Path | None:
    payload = invoice_editor_payload(connection, invoice_id)
    if payload is None:
        return None
    invoice = payload["invoice"]
    if not invoice["issued_at"]:
        raise ValueError("Invoice PDF is not available until the invoice is issued.")
    pdf_file_name = str(invoice["pdf_file_name"] or f"{slugify_invoice_number(str(invoice['invoice_number']))}.pdf")
    pdf_path = invoice_pdf_directory(data_dir) / pdf_file_name
    if not pdf_path.exists():
        pdf_path = write_invoice_pdf(data_dir, payload)
    return pdf_path