from __future__ import annotations

from io import BytesIO
import sqlite3
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from .date_utils import utc_now
from .invoices import invoice_select_sql, row_to_invoice
from .overview import overview_bootstrap_payload


SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

ET.register_namespace("", SPREADSHEET_NS)
ET.register_namespace("r", OFFICE_DOC_REL_NS)

def customer_statement_select_sql() -> str:
    return """
    SELECT
        c.id,
        c.customer_name,
        c.contact_name,
        c.email,
        c.phone,
        c.street_address,
        c.city,
        c.state,
        c.zip,
        COALESCE(c.notes, '') AS notes,
        COALESCE((
            SELECT SUM(ibv.open_amount_cents)
            FROM invoices i
            JOIN invoice_balance_view ibv ON ibv.invoice_id = i.id
            WHERE i.customer_id = c.id AND i.issued_at IS NOT NULL
        ), 0) AS open_ar_cents,
        COALESCE((
            SELECT SUM(puv.unapplied_amount_cents)
            FROM payment_unapplied_view puv
            WHERE puv.customer_id = c.id
        ), 0) AS unapplied_credit_cents,
        COALESCE((
            SELECT SUM(ibv.open_amount_cents)
            FROM invoices i
            JOIN invoice_balance_view ibv ON ibv.invoice_id = i.id
            WHERE i.customer_id = c.id AND i.issued_at IS NOT NULL
        ), 0) - COALESCE((
            SELECT SUM(puv.unapplied_amount_cents)
            FROM payment_unapplied_view puv
            WHERE puv.customer_id = c.id
        ), 0) AS net_balance_cents,
        COALESCE((
            SELECT COUNT(*)
            FROM invoices i
            JOIN invoice_balance_view ibv ON ibv.invoice_id = i.id
            WHERE i.customer_id = c.id AND i.issued_at IS NOT NULL AND ibv.open_amount_cents > 0
        ), 0) AS open_invoice_count,
        (
            SELECT MAX(i.invoice_date)
            FROM invoices i
            WHERE i.customer_id = c.id
        ) AS last_invoice_date,
        (
            SELECT MAX(p.payment_date)
            FROM payments p
            WHERE p.customer_id = c.id
        ) AS last_payment_date,
        c.updated_at
    FROM customers c
    """


def row_to_statement_customer(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "customer_name": row["customer_name"],
        "contact_name": row["contact_name"],
        "email": row["email"],
        "phone": row["phone"],
        "street_address": row["street_address"],
        "city": row["city"],
        "state": row["state"],
        "zip": row["zip"],
        "notes": row["notes"],
        "open_ar_cents": int(row["open_ar_cents"] or 0),
        "unapplied_credit_cents": int(row["unapplied_credit_cents"] or 0),
        "net_balance_cents": int(row["net_balance_cents"] or 0),
        "open_invoice_count": int(row["open_invoice_count"] or 0),
        "last_invoice_date": row["last_invoice_date"],
        "last_payment_date": row["last_payment_date"],
        "updated_at": row["updated_at"],
    }


def fetch_statement_customers(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        customer_statement_select_sql() + " ORDER BY open_ar_cents DESC, net_balance_cents DESC, c.customer_name COLLATE NOCASE, c.id"
    ).fetchall()
    return [row_to_statement_customer(row) for row in rows]


def fetch_statement_customer(connection: sqlite3.Connection, customer_id: int) -> dict[str, object] | None:
    row = connection.execute(customer_statement_select_sql() + " WHERE c.id = ?", (customer_id,)).fetchone()
    if row is None:
        return None
    return row_to_statement_customer(row)


def fetch_statement_invoices(connection: sqlite3.Connection, customer_id: int) -> list[dict[str, object]]:
    rows = connection.execute(
        invoice_select_sql() + " WHERE i.customer_id = ? AND i.issued_at IS NOT NULL ORDER BY i.invoice_date DESC, i.id DESC",
        (customer_id,),
    ).fetchall()
    invoices = [row_to_invoice(connection, row) for row in rows]
    return [invoice for invoice in invoices if int(invoice["invoice_amount_cents"] or 0) > 0]


def fetch_statement_unapplied_payments(connection: sqlite3.Connection, customer_id: int) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            p.id,
            p.payment_date,
            p.reference_number,
            p.amount_cents,
            COALESCE(puv.applied_amount_cents, 0) AS applied_amount_cents,
            COALESCE(puv.unapplied_amount_cents, 0) AS unapplied_amount_cents,
            COALESCE(p.notes, '') AS notes,
            p.updated_at
        FROM payments p
        JOIN payment_unapplied_view puv ON puv.payment_id = p.id
        WHERE p.customer_id = ? AND puv.unapplied_amount_cents > 0
        ORDER BY p.payment_date DESC, p.id DESC
        """,
        (customer_id,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "payment_date": row["payment_date"],
            "reference_number": row["reference_number"],
            "amount_cents": int(row["amount_cents"] or 0),
            "applied_amount_cents": int(row["applied_amount_cents"] or 0),
            "unapplied_amount_cents": int(row["unapplied_amount_cents"] or 0),
            "notes": row["notes"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def statement_totals(customer: dict[str, object], invoices: list[dict[str, object]], unapplied_payments: list[dict[str, object]]) -> dict[str, object]:
    return {
        "open_ar_cents": int(customer["open_ar_cents"]),
        "unapplied_credit_cents": int(customer["unapplied_credit_cents"]),
        "net_balance_cents": int(customer["net_balance_cents"]),
        "issued_invoice_count": len(invoices),
        "open_invoice_count": sum(1 for invoice in invoices if int(invoice["open_balance_cents"] or 0) > 0),
        "unapplied_payment_count": len(unapplied_payments),
    }


def accounts_receivable_report_payload(connection: sqlite3.Connection, customer_id: int | None = None) -> dict[str, object]:
    customers = fetch_statement_customers(connection)
    selected_customer_id = customer_id
    if selected_customer_id is None and customers:
        selected_customer_id = next(
            (customer["id"] for customer in customers if customer["open_ar_cents"] or customer["unapplied_credit_cents"]),
            customers[0]["id"],
        )

    total_open_ar_cents = sum(int(customer["open_ar_cents"]) for customer in customers)
    total_unapplied_credit_cents = sum(int(customer["unapplied_credit_cents"]) for customer in customers)
    statement = None
    if selected_customer_id is not None:
        customer = fetch_statement_customer(connection, selected_customer_id)
        if customer is not None:
            invoices = fetch_statement_invoices(connection, selected_customer_id)
            unapplied_payments = fetch_statement_unapplied_payments(connection, selected_customer_id)
            statement = {
                "customer": customer,
                "invoices": invoices,
                "unapplied_payments": unapplied_payments,
                "totals": statement_totals(customer, invoices, unapplied_payments),
                "generated_at": utc_now(),
            }

    return {
        "summary": {
            "total_open_ar_cents": total_open_ar_cents,
            "total_unapplied_credit_cents": total_unapplied_credit_cents,
            "net_receivables_cents": total_open_ar_cents - total_unapplied_credit_cents,
            "customers_with_balance_count": sum(1 for customer in customers if customer["open_ar_cents"] or customer["unapplied_credit_cents"]),
        },
        "customers": customers,
        "selected_customer_id": selected_customer_id,
        "statement": statement,
        "audit_export_path": "/api/exports/audit.xlsx",
    }


def rows_as_dicts(connection: sqlite3.Connection, query: str, parameters: tuple[object, ...] = ()) -> list[dict[str, object]]:
    return [dict(row) for row in connection.execute(query, parameters).fetchall()]


def row_values(row: dict[str, object], headers: list[str]) -> list[object]:
    return [row.get(header) for header in headers]


def build_open_invoice_sheet(connection: sqlite3.Connection) -> list[list[object]]:
    rows = connection.execute(
        invoice_select_sql() + " WHERE i.issued_at IS NOT NULL ORDER BY i.invoice_date DESC, i.id DESC"
    ).fetchall()
    invoices = [row_to_invoice(connection, row) for row in rows]
    headers = [
        "id",
        "invoice_number",
        "customer_name",
        "project_number",
        "invoice_date",
        "terms_days",
        "status",
        "invoice_amount_cents",
        "paid_amount_cents",
        "open_balance_cents",
        "prior_balance_cents",
        "unapplied_credit_cents",
        "pdf_file_name",
        "issued_at",
        "updated_at",
    ]
    return [headers, *[row_values(invoice, headers) for invoice in invoices]]


def build_overview_sheet(connection: sqlite3.Connection) -> list[list[object]]:
    summary = overview_bootstrap_payload(connection)["summary"]
    report_summary = accounts_receivable_report_payload(connection)["summary"]
    rows = [["metric", "value"]]
    for key, value in summary.items():
        rows.append([key, value])
    for key, value in report_summary.items():
        rows.append([key, value])
    return rows


def build_workbook_sheets(connection: sqlite3.Connection) -> list[tuple[str, list[list[object]]]]:
    customer_rows = fetch_statement_customers(connection)
    customer_headers = [
        "id",
        "customer_name",
        "contact_name",
        "email",
        "phone",
        "street_address",
        "city",
        "state",
        "zip",
        "open_ar_cents",
        "unapplied_credit_cents",
        "net_balance_cents",
        "open_invoice_count",
        "last_invoice_date",
        "last_payment_date",
        "updated_at",
    ]

    sheet_definitions: list[tuple[str, list[list[object]]]] = [
        ("Overview", build_overview_sheet(connection)),
        ("CustomerBalances", [customer_headers, *[row_values(row, customer_headers) for row in customer_rows]]),
        (
            "UnappliedPayments",
            [
                [
                    "payment_id",
                    "customer_id",
                    "amount_cents",
                    "applied_amount_cents",
                    "unapplied_amount_cents",
                ],
                *[
                    row_values(row, ["payment_id", "customer_id", "amount_cents", "applied_amount_cents", "unapplied_amount_cents"])
                    for row in rows_as_dicts(connection, "SELECT * FROM payment_unapplied_view ORDER BY customer_id, payment_id")
                ],
            ],
        ),
        ("OpenInvoices", build_open_invoice_sheet(connection)),
        ("Customers", build_query_sheet(connection, "SELECT * FROM customers ORDER BY id")),
        ("Projects", build_query_sheet(connection, "SELECT * FROM projects ORDER BY id")),
        ("ProjectRates", build_query_sheet(connection, "SELECT * FROM project_rates ORDER BY project_id, sort_order, id")),
        ("TimeEntries", build_query_sheet(connection, "SELECT * FROM time_entries ORDER BY entry_date DESC, id DESC")),
        ("Expenses", build_query_sheet(connection, "SELECT * FROM expenses ORDER BY entry_date DESC, id DESC")),
        ("Invoices", build_query_sheet(connection, "SELECT * FROM invoices ORDER BY invoice_date DESC, id DESC")),
        ("Payments", build_query_sheet(connection, "SELECT * FROM payments ORDER BY payment_date DESC, id DESC")),
        (
            "PaymentApplications",
            build_query_sheet(connection, "SELECT * FROM payment_applications ORDER BY applied_at DESC, id DESC"),
        ),
    ]
    return sheet_definitions


def build_query_sheet(connection: sqlite3.Connection, query: str, parameters: tuple[object, ...] = ()) -> list[list[object]]:
    rows = connection.execute(query, parameters).fetchall()
    if not rows:
        return [[]]
    headers = list(rows[0].keys())
    return [headers, *[[row[key] for key in headers] for row in rows]]


def column_name(index: int) -> str:
    name = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def worksheet_xml(rows: list[list[object]]) -> bytes:
    worksheet = ET.Element(f"{{{SPREADSHEET_NS}}}worksheet")
    sheet_data = ET.SubElement(worksheet, f"{{{SPREADSHEET_NS}}}sheetData")

    for row_index, row in enumerate(rows, start=1):
        row_element = ET.SubElement(sheet_data, f"{{{SPREADSHEET_NS}}}row", {"r": str(row_index)})
        for column_index, value in enumerate(row, start=1):
            if value is None:
                continue
            cell = ET.SubElement(
                row_element,
                f"{{{SPREADSHEET_NS}}}c",
                {"r": f"{column_name(column_index)}{row_index}"},
            )
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                ET.SubElement(cell, f"{{{SPREADSHEET_NS}}}v").text = str(value)
            else:
                cell.set("t", "inlineStr")
                inline_string = ET.SubElement(cell, f"{{{SPREADSHEET_NS}}}is")
                ET.SubElement(inline_string, f"{{{SPREADSHEET_NS}}}t").text = str(value)

    return ET.tostring(worksheet, encoding="utf-8", xml_declaration=True)


def workbook_xml(sheet_names: list[str]) -> bytes:
    workbook = ET.Element(f"{{{SPREADSHEET_NS}}}workbook")
    sheets = ET.SubElement(workbook, f"{{{SPREADSHEET_NS}}}sheets")
    for index, name in enumerate(sheet_names, start=1):
        ET.SubElement(
            sheets,
            f"{{{SPREADSHEET_NS}}}sheet",
            {
                "name": name[:31],
                "sheetId": str(index),
                f"{{{OFFICE_DOC_REL_NS}}}id": f"rId{index}",
            },
        )
    return ET.tostring(workbook, encoding="utf-8", xml_declaration=True)


def workbook_relationships_xml(sheet_count: int) -> bytes:
    relationships = ET.Element("Relationships", xmlns=PACKAGE_REL_NS)
    for index in range(1, sheet_count + 1):
        ET.SubElement(
            relationships,
            "Relationship",
            {
                "Id": f"rId{index}",
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
                "Target": f"worksheets/sheet{index}.xml",
            },
        )
    return ET.tostring(relationships, encoding="utf-8", xml_declaration=True)


def root_relationships_xml() -> bytes:
    relationships = ET.Element("Relationships", xmlns=PACKAGE_REL_NS)
    ET.SubElement(
        relationships,
        "Relationship",
        {
            "Id": "rId1",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
            "Target": "xl/workbook.xml",
        },
    )
    return ET.tostring(relationships, encoding="utf-8", xml_declaration=True)


def content_types_xml(sheet_count: int) -> bytes:
    content_types = ET.Element("Types", xmlns=CONTENT_TYPES_NS)
    ET.SubElement(content_types, "Default", {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
    ET.SubElement(content_types, "Default", {"Extension": "xml", "ContentType": "application/xml"})
    ET.SubElement(
        content_types,
        "Override",
        {
            "PartName": "/xl/workbook.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
        },
    )
    for index in range(1, sheet_count + 1):
        ET.SubElement(
            content_types,
            "Override",
            {
                "PartName": f"/xl/worksheets/sheet{index}.xml",
                "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
            },
        )
    return ET.tostring(content_types, encoding="utf-8", xml_declaration=True)


def build_audit_export_bytes(connection: sqlite3.Connection) -> bytes:
    sheets = build_workbook_sheets(connection)
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as workbook_zip:
        workbook_zip.writestr("[Content_Types].xml", content_types_xml(len(sheets)))
        workbook_zip.writestr("_rels/.rels", root_relationships_xml())
        workbook_zip.writestr("xl/workbook.xml", workbook_xml([name for name, _rows in sheets]))
        workbook_zip.writestr("xl/_rels/workbook.xml.rels", workbook_relationships_xml(len(sheets)))
        for index, (_name, rows) in enumerate(sheets, start=1):
            workbook_zip.writestr(f"xl/worksheets/sheet{index}.xml", worksheet_xml(rows))
    return buffer.getvalue()