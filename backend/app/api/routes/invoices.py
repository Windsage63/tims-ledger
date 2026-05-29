from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.errors import ConflictError, NotFoundError
from app.db.session import get_session
from app.models import BillingStatus, Customer, Expense, Invoice, TimeEntry
from app.schemas.invoices import (
    InvoiceCandidatesRead,
    InvoiceCreate,
    InvoiceDetailRead,
    InvoiceIssue,
    InvoiceRead,
)
from app.services import AccountingError, create_draft_invoice_from_sources, issue_invoice

router = APIRouter(prefix="/invoices", tags=["invoices"])
candidate_router = APIRouter(prefix="/invoice-builder", tags=["invoice builder"])


@candidate_router.get("/candidates", response_model=InvoiceCandidatesRead)
def get_invoice_candidates(
    session: Annotated[Session, Depends(get_session)],
    customer_id: int,
    project_id: Annotated[int | None, Query(gt=0)] = None,
) -> dict:
    _ensure_customer_exists(session, customer_id)

    time_query = select(TimeEntry).where(
        TimeEntry.customer_id == customer_id,
        TimeEntry.billable.is_(True),
        TimeEntry.billing_status == BillingStatus.UNBILLED.value,
    )
    expense_query = select(Expense).where(
        Expense.customer_id == customer_id,
        Expense.billable.is_(True),
        Expense.reimbursable.is_(True),
        Expense.reimbursement_status == BillingStatus.UNBILLED.value,
    )

    if project_id is not None:
        time_query = time_query.where(TimeEntry.project_id == project_id)
        expense_query = expense_query.where(Expense.project_id == project_id)

    return {
        "customer_id": customer_id,
        "project_id": project_id,
        "time_entries": list(session.scalars(time_query.order_by(TimeEntry.date, TimeEntry.id))),
        "expenses": list(session.scalars(expense_query.order_by(Expense.date, Expense.id))),
    }


@router.get("", response_model=list[InvoiceRead])
def list_invoices(
    session: Annotated[Session, Depends(get_session)],
    customer_id: int | None = None,
    status: Annotated[str | None, Query(max_length=40)] = None,
) -> list[Invoice]:
    query = select(Invoice).order_by(Invoice.invoice_date.desc(), Invoice.invoice_no.desc())
    if customer_id is not None:
        query = query.where(Invoice.customer_id == customer_id)
    if status:
        query = query.where(Invoice.status == status)
    return list(session.scalars(query))


@router.post("", response_model=InvoiceDetailRead, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Invoice:
    _ensure_customer_exists(session, payload.customer_id)
    if session.scalar(select(Invoice).where(Invoice.invoice_no == payload.invoice_no)) is not None:
        raise ConflictError("Invoice number already exists.")

    try:
        invoice = create_draft_invoice_from_sources(
            session,
            invoice_no=payload.invoice_no,
            customer_id=payload.customer_id,
            invoice_date=payload.invoice_date,
            time_entry_ids=payload.time_entry_ids,
            expense_ids=payload.expense_ids,
            due_date=payload.due_date,
            terms=payload.terms,
        )
    except AccountingError as exc:
        session.rollback()
        raise ConflictError(str(exc)) from exc

    session.commit()
    return _get_invoice_detail(session, invoice.id)


@router.get("/{invoice_id}", response_model=InvoiceDetailRead)
def get_invoice(
    invoice_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> Invoice:
    return _get_invoice_detail(session, invoice_id)


@router.post("/{invoice_id}/issue", response_model=InvoiceDetailRead)
@router.post("/{invoice_id}/send", response_model=InvoiceDetailRead, include_in_schema=False)
def issue_invoice_route(
    invoice_id: int,
    payload: InvoiceIssue,
    session: Annotated[Session, Depends(get_session)],
) -> Invoice:
    try:
        invoice = issue_invoice(session, invoice_id, issued_date=payload.sent_date)
    except AccountingError as exc:
        session.rollback()
        message = str(exc)
        if message == "Invoice was not found.":
            raise NotFoundError(message) from exc
        raise ConflictError(message) from exc

    session.commit()
    return _get_invoice_detail(session, invoice.id)


def _get_invoice_detail(session: Session, invoice_id: int) -> Invoice:
    invoice = session.scalar(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(selectinload(Invoice.lines))
    )
    if invoice is None:
        raise NotFoundError("Invoice was not found.")
    return invoice


def _ensure_customer_exists(session: Session, customer_id: int) -> None:
    if session.get(Customer, customer_id) is None:
        raise NotFoundError("Customer was not found.")
