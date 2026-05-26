import csv
from io import StringIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, Invoice
from app.services.balances import OPEN_INVOICE_STATUSES, ar_aging


def ar_aging_csv(session: Session, as_of_date) -> str:
    report = ar_aging(session, as_of_date)
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "Customer ID",
            "Customer",
            "Current",
            "1-30",
            "31-60",
            "61-90",
            "Over 90",
            "Total",
        ]
    )
    for row in report["customers"]:
        writer.writerow(
            [
                row["customer_id"],
                row["customer_name"],
                row["current"],
                row["days_1_30"],
                row["days_31_60"],
                row["days_61_90"],
                row["days_over_90"],
                row["total"],
            ]
        )
    writer.writerow(["", "TOTAL", "", "", "", "", "", report["total"]])
    return output.getvalue()


def open_invoices_csv(session: Session) -> str:
    rows = session.execute(
        select(Invoice, Customer)
        .join(Customer, Customer.id == Invoice.customer_id)
        .where(Invoice.status.in_(OPEN_INVOICE_STATUSES), Invoice.open_balance > 0)
        .order_by(Customer.name, Invoice.invoice_date, Invoice.invoice_no)
    )
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "Customer ID",
            "Customer",
            "Invoice ID",
            "Invoice No",
            "Invoice Date",
            "Due Date",
            "Status",
            "Total",
            "Open Balance",
        ]
    )
    for invoice, customer in rows:
        writer.writerow(
            [
                customer.id,
                customer.name,
                invoice.id,
                invoice.invoice_no,
                invoice.invoice_date,
                invoice.due_date or "",
                invoice.status,
                invoice.total,
                invoice.open_balance,
            ]
        )
    return output.getvalue()
