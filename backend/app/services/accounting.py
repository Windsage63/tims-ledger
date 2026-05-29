from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BillingStatus,
    Expense,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Payment,
    PaymentApplication,
    TimeEntry,
)

CENTS = Decimal("0.01")


class AccountingError(ValueError):
    """Raised when an accounting workflow would create invalid books."""


@dataclass(frozen=True)
class PaymentApplicationInput:
    invoice_id: int
    amount: Decimal
    notes: str | None = None


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def create_draft_invoice_from_sources(
    session: Session,
    *,
    invoice_no: str,
    customer_id: int,
    invoice_date: date,
    time_entry_ids: list[int] | None = None,
    expense_ids: list[int] | None = None,
    due_date: date | None = None,
    terms: str = "Due on receipt",
) -> Invoice:
    time_entries = _load_time_entries(session, time_entry_ids or [])
    expenses = _load_expenses(session, expense_ids or [])

    if not time_entries and not expenses:
        raise AccountingError("Invoice cannot be created without time entries or expenses.")

    for entry in time_entries:
        if entry.customer_id != customer_id:
            raise AccountingError("Time entry belongs to a different customer.")
        if not entry.billable or entry.billing_status != BillingStatus.UNBILLED.value:
            raise AccountingError("Time entry is not available for invoicing.")

    for expense in expenses:
        if expense.customer_id != customer_id:
            raise AccountingError("Expense belongs to a different customer.")
        if (
            not expense.billable
            or not expense.reimbursable
            or expense.reimbursement_status != BillingStatus.UNBILLED.value
        ):
            raise AccountingError("Expense is not available for invoicing.")

    invoice = Invoice(
        invoice_no=invoice_no,
        customer_id=customer_id,
        invoice_date=invoice_date,
        due_date=due_date,
        terms=terms,
        status=InvoiceStatus.DRAFT.value,
    )
    session.add(invoice)
    session.flush()

    subtotal_labor = Decimal("0.00")
    subtotal_expenses = Decimal("0.00")
    sort_order = 1

    for entry in time_entries:
        amount = money(entry.hours * entry.rate)
        subtotal_labor += amount
        invoice.lines.append(
            InvoiceLine(
                source_type="time_entry",
                source_id=entry.id,
                description=entry.description,
                qty=entry.hours,
                unit_price=entry.rate,
                amount=amount,
                line_group="labor",
                sort_order=sort_order,
            )
        )
        entry.invoice_id = invoice.id
        entry.billing_status = BillingStatus.ASSIGNED.value
        sort_order += 1

    for expense in expenses:
        amount = money(expense.total)
        subtotal_expenses += amount
        invoice.lines.append(
            InvoiceLine(
                source_type="expense",
                source_id=expense.id,
                description=expense.description,
                qty=expense.qty,
                unit_price=expense.unit_cost,
                amount=amount,
                line_group="expenses",
                sort_order=sort_order,
            )
        )
        expense.invoice_id = invoice.id
        expense.reimbursement_status = BillingStatus.ASSIGNED.value
        sort_order += 1

    invoice.subtotal_labor = money(subtotal_labor)
    invoice.subtotal_expenses = money(subtotal_expenses)
    invoice.total = money(
        invoice.subtotal_labor
        + invoice.subtotal_expenses
        + invoice.freight
        + invoice.per_diem
        + invoice.other
        + invoice.sales_tax
    )
    invoice.open_balance = invoice.total
    session.flush()
    return invoice


def issue_invoice(session: Session, invoice_id: int, *, issued_date: date) -> Invoice:
    invoice = session.get(Invoice, invoice_id)
    if invoice is None:
        raise AccountingError("Invoice was not found.")
    if invoice.status != InvoiceStatus.DRAFT.value:
        raise AccountingError("Only draft invoices can be issued.")
    if not invoice.lines:
        raise AccountingError("Invoice cannot be issued with no line items.")

    invoice.status = InvoiceStatus.ISSUED.value
    invoice.sent_date = issued_date

    session.flush()
    return invoice


def send_invoice(session: Session, invoice_id: int, *, sent_date: date) -> Invoice:
    return issue_invoice(session, invoice_id, issued_date=sent_date)


def apply_payment(
    session: Session,
    *,
    payment_id: int,
    application_date: date,
    applications: list[PaymentApplicationInput],
) -> Payment:
    if not applications:
        raise AccountingError("Payment application requires at least one invoice.")

    payment = session.get(Payment, payment_id)
    if payment is None:
        raise AccountingError("Payment was not found.")

    total_to_apply = money(sum((item.amount for item in applications), Decimal("0.00")))
    if total_to_apply <= 0:
        raise AccountingError("Payment application amount must be positive.")
    if total_to_apply > money(payment.unapplied_amount):
        raise AccountingError("Payment application exceeds unapplied payment amount.")

    invoices = {
        invoice.id: invoice
        for invoice in session.scalars(
            select(Invoice).where(Invoice.id.in_([item.invoice_id for item in applications]))
        )
    }

    for item in applications:
        amount = money(item.amount)
        invoice = invoices.get(item.invoice_id)
        if invoice is None:
            raise AccountingError("Invoice was not found.")
        if invoice.customer_id != payment.customer_id:
            raise AccountingError("Payment cannot be applied to another customer's invoice.")
        if invoice.status not in {
            InvoiceStatus.ISSUED.value,
            InvoiceStatus.SENT.value,
            InvoiceStatus.PARTIALLY_PAID.value,
        }:
            raise AccountingError("Payment can only be applied to issued or partially paid invoices.")
        if amount <= 0:
            raise AccountingError("Payment application amount must be positive.")
        if amount > money(invoice.open_balance):
            raise AccountingError("Payment application exceeds invoice open balance.")

    for item in applications:
        amount = money(item.amount)
        invoice = invoices[item.invoice_id]
        session.add(
            PaymentApplication(
                payment_id=payment.id,
                invoice_id=invoice.id,
                application_date=application_date,
                amount_applied=amount,
                notes=item.notes,
            )
        )
        invoice.open_balance = money(invoice.open_balance - amount)
        invoice.status = (
            InvoiceStatus.PAID.value
            if invoice.open_balance == Decimal("0.00")
            else InvoiceStatus.PARTIALLY_PAID.value
        )

    payment.unapplied_amount = money(payment.unapplied_amount - total_to_apply)
    session.flush()
    return payment


def _load_time_entries(session: Session, ids: list[int]) -> list[TimeEntry]:
    if not ids:
        return []
    entries = list(session.scalars(select(TimeEntry).where(TimeEntry.id.in_(ids))))
    if len(entries) != len(set(ids)):
        raise AccountingError("One or more time entries were not found.")
    return entries


def _load_expenses(session: Session, ids: list[int]) -> list[Expense]:
    if not ids:
        return []
    expenses = list(session.scalars(select(Expense).where(Expense.id.in_(ids))))
    if len(expenses) != len(set(ids)):
        raise AccountingError("One or more expenses were not found.")
    return expenses
