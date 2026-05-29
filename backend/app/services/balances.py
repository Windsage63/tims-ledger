from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, Invoice, InvoiceStatus, Payment
from app.services.accounting import money

OPEN_INVOICE_STATUSES = {
    InvoiceStatus.ISSUED.value,
    InvoiceStatus.SENT.value,
    InvoiceStatus.PARTIALLY_PAID.value,
    InvoiceStatus.OVERDUE.value,
}


def customer_balance(session: Session, customer_id: int) -> dict:
    invoices = list(
        session.scalars(
            select(Invoice).where(
                Invoice.customer_id == customer_id,
                Invoice.status.in_(OPEN_INVOICE_STATUSES),
                Invoice.open_balance > 0,
            )
        )
    )
    payments = list(
        session.scalars(
            select(Payment).where(
                Payment.customer_id == customer_id,
                Payment.unapplied_amount > 0,
            )
        )
    )
    open_ar = money(sum((invoice.open_balance for invoice in invoices), Decimal("0.00")))
    unapplied_credits = money(
        sum((payment.unapplied_amount for payment in payments), Decimal("0.00"))
    )
    return {
        "customer_id": customer_id,
        "open_ar": open_ar,
        "unapplied_credits": unapplied_credits,
        "net_balance": money(open_ar - unapplied_credits),
        "open_invoice_count": len(invoices),
        "unapplied_payment_count": len(payments),
    }


def ar_aging(session: Session, as_of_date: date) -> dict:
    rows = []
    total = Decimal("0.00")
    customers = list(session.scalars(select(Customer).order_by(Customer.name)))
    for customer in customers:
        invoices = list(
            session.scalars(
                select(Invoice).where(
                    Invoice.customer_id == customer.id,
                    Invoice.status.in_(OPEN_INVOICE_STATUSES),
                    Invoice.open_balance > 0,
                )
            )
        )
        buckets = {
            "current": Decimal("0.00"),
            "days_1_30": Decimal("0.00"),
            "days_31_60": Decimal("0.00"),
            "days_61_90": Decimal("0.00"),
            "days_over_90": Decimal("0.00"),
        }
        for invoice in invoices:
            days_old = (as_of_date - (invoice.due_date or invoice.invoice_date)).days
            bucket = _aging_bucket(days_old)
            buckets[bucket] += invoice.open_balance

        customer_total = money(sum(buckets.values(), Decimal("0.00")))
        if customer_total == Decimal("0.00"):
            continue
        total += customer_total
        rows.append(
            {
                "customer_id": customer.id,
                "customer_name": customer.name,
                **{key: money(value) for key, value in buckets.items()},
                "total": customer_total,
            }
        )

    return {"as_of_date": as_of_date, "customers": rows, "total": money(total)}


def _aging_bucket(days_old: int) -> str:
    if days_old <= 0:
        return "current"
    if days_old <= 30:
        return "days_1_30"
    if days_old <= 60:
        return "days_31_60"
    if days_old <= 90:
        return "days_61_90"
    return "days_over_90"
