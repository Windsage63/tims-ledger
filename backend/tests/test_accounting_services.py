from datetime import date
from decimal import Decimal

import pytest

from app.models import (
    BillingStatus,
    Customer,
    Expense,
    InvoiceStatus,
    Payment,
    PaymentType,
    Project,
    TimeEntry,
)
from app.services import (
    AccountingError,
    PaymentApplicationInput,
    apply_payment,
    create_draft_invoice_from_sources,
    send_invoice,
)


def test_invoice_draft_links_source_records_and_totals(session) -> None:
    customer = Customer(name="Air Advantage")
    project = Project(
        customer=customer,
        project_no="AA-001",
        name="Tower work",
        default_hourly_rate=Decimal("125.00"),
    )
    time_entry = TimeEntry(
        customer_id=1,
        project=project,
        date=date(2026, 5, 1),
        description="Field labor",
        hours=Decimal("2.50"),
        rate=Decimal("125.00"),
    )
    expense = Expense(
        customer_id=1,
        project=project,
        date=date(2026, 5, 2),
        description="Cable",
        qty=Decimal("1.00"),
        unit_cost=Decimal("42.10"),
        total=Decimal("42.10"),
    )
    session.add_all([customer, project, time_entry, expense])
    session.flush()

    invoice = create_draft_invoice_from_sources(
        session,
        invoice_no="662",
        customer_id=customer.id,
        invoice_date=date(2026, 5, 7),
        time_entry_ids=[time_entry.id],
        expense_ids=[expense.id],
    )

    assert invoice.status == InvoiceStatus.DRAFT.value
    assert invoice.subtotal_labor == Decimal("312.50")
    assert invoice.subtotal_expenses == Decimal("42.10")
    assert invoice.total == Decimal("354.60")
    assert invoice.open_balance == Decimal("354.60")
    assert len(invoice.lines) == 2
    assert time_entry.invoice_id == invoice.id
    assert time_entry.billing_status == BillingStatus.ASSIGNED.value
    assert expense.invoice_id == invoice.id
    assert expense.reimbursement_status == BillingStatus.ASSIGNED.value


def test_send_invoice_publishes_invoice_without_restamping_source_records(session) -> None:
    customer = Customer(name="Air Advantage")
    project = Project(customer=customer, project_no="AA-001", name="Tower work")
    time_entry = TimeEntry(
        customer=customer,
        project=project,
        date=date(2026, 5, 1),
        description="Field labor",
        hours=Decimal("1.00"),
        rate=Decimal("100.00"),
    )
    session.add_all([customer, project, time_entry])
    session.flush()
    invoice = create_draft_invoice_from_sources(
        session,
        invoice_no="662",
        customer_id=customer.id,
        invoice_date=date(2026, 5, 7),
        time_entry_ids=[time_entry.id],
    )

    send_invoice(session, invoice.id, sent_date=date(2026, 5, 8))

    assert invoice.status == InvoiceStatus.ISSUED.value
    assert invoice.sent_date == date(2026, 5, 8)
    assert time_entry.billing_status == BillingStatus.ASSIGNED.value


def test_payment_application_updates_invoice_and_unapplied_amount(session) -> None:
    invoice, payment = _sent_invoice_with_payment(session)

    apply_payment(
        session,
        payment_id=payment.id,
        application_date=date(2026, 5, 10),
        applications=[PaymentApplicationInput(invoice_id=invoice.id, amount=Decimal("75.00"))],
    )

    assert invoice.status == InvoiceStatus.PARTIALLY_PAID.value
    assert invoice.open_balance == Decimal("25.00")
    assert payment.unapplied_amount == Decimal("25.00")

    apply_payment(
        session,
        payment_id=payment.id,
        application_date=date(2026, 5, 11),
        applications=[PaymentApplicationInput(invoice_id=invoice.id, amount=Decimal("25.00"))],
    )

    assert invoice.status == InvoiceStatus.PAID.value
    assert invoice.open_balance == Decimal("0.00")
    assert payment.unapplied_amount == Decimal("0.00")


def test_payment_application_rejects_overapplication(session) -> None:
    invoice, payment = _sent_invoice_with_payment(session, payment_amount=Decimal("150.00"))

    with pytest.raises(AccountingError, match="exceeds invoice open balance"):
        apply_payment(
            session,
            payment_id=payment.id,
            application_date=date(2026, 5, 10),
            applications=[PaymentApplicationInput(invoice_id=invoice.id, amount=Decimal("125.00"))],
        )

    assert invoice.open_balance == Decimal("100.00")
    assert payment.unapplied_amount == Decimal("150.00")


def _sent_invoice_with_payment(session, payment_amount: Decimal = Decimal("100.00")):
    customer = Customer(name="Air Advantage")
    project = Project(customer=customer, project_no="AA-001", name="Tower work")
    time_entry = TimeEntry(
        customer=customer,
        project=project,
        date=date(2026, 5, 1),
        description="Field labor",
        hours=Decimal("1.00"),
        rate=Decimal("100.00"),
    )
    payment = Payment(
        customer=customer,
        payment_date=date(2026, 5, 9),
        payment_type=PaymentType.CUSTOMER_PAYMENT.value,
        amount_received=payment_amount,
        unapplied_amount=payment_amount,
    )
    session.add_all([customer, project, time_entry, payment])
    session.flush()
    invoice = create_draft_invoice_from_sources(
        session,
        invoice_no="662",
        customer_id=customer.id,
        invoice_date=date(2026, 5, 7),
        time_entry_ids=[time_entry.id],
    )
    send_invoice(session, invoice.id, sent_date=date(2026, 5, 8))
    return invoice, payment
