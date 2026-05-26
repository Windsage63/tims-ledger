from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import ConflictError, NotFoundError
from app.db.session import get_session
from app.models import BillingStatus, Expense, ExpenseCategory, Project
from app.schemas.expenses import ExpenseCreate, ExpenseRead, ExpenseUpdate
from app.services import money

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("", response_model=list[ExpenseRead])
def list_expenses(
    session: Annotated[Session, Depends(get_session)],
    customer_id: int | None = None,
    project_id: int | None = None,
    reimbursement_status: Annotated[str | None, Query(max_length=40)] = None,
    unbilled_only: bool = False,
) -> list[Expense]:
    query = select(Expense).order_by(Expense.date, Expense.id)
    if customer_id is not None:
        query = query.where(Expense.customer_id == customer_id)
    if project_id is not None:
        query = query.where(Expense.project_id == project_id)
    if reimbursement_status:
        query = query.where(Expense.reimbursement_status == reimbursement_status)
    if unbilled_only:
        query = query.where(
            Expense.billable.is_(True),
            Expense.reimbursable.is_(True),
            Expense.reimbursement_status == BillingStatus.UNBILLED.value,
        )
    return list(session.scalars(query))


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Expense:
    project = _get_project(session, payload.project_id)
    _ensure_category_exists(session, payload.category_id)
    total = _resolve_total(payload.qty, payload.unit_cost, payload.total)
    reimbursement_status = _resolve_reimbursement_status(payload.billable, payload.reimbursable)
    expense = Expense(
        **payload.model_dump(exclude={"total"}),
        customer_id=project.customer_id,
        total=total,
        reimbursement_status=reimbursement_status,
    )
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(
    expense_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> Expense:
    return _get_expense(session, expense_id)


@router.patch("/{expense_id}", response_model=ExpenseRead)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    session: Annotated[Session, Depends(get_session)],
) -> Expense:
    expense = _get_expense(session, expense_id)
    _ensure_expense_editable(expense)
    updates = payload.model_dump(exclude_unset=True)

    if "project_id" in updates:
        project = _get_project(session, updates["project_id"])
        expense.customer_id = project.customer_id

    if "category_id" in updates:
        _ensure_category_exists(session, updates["category_id"])

    if any(field in updates for field in {"qty", "unit_cost", "total"}):
        qty = updates.get("qty", expense.qty)
        unit_cost = updates.get("unit_cost", expense.unit_cost)
        total = updates.pop("total", None)
        expense.total = _resolve_total(qty, unit_cost, total)

    if "billable" in updates or "reimbursable" in updates:
        billable = updates.get("billable", expense.billable)
        reimbursable = updates.get("reimbursable", expense.reimbursable)
        expense.reimbursement_status = _resolve_reimbursement_status(billable, reimbursable)

    for field, value in updates.items():
        setattr(expense, field, value)

    session.commit()
    session.refresh(expense)
    return expense


def _get_expense(session: Session, expense_id: int) -> Expense:
    expense = session.get(Expense, expense_id)
    if expense is None:
        raise NotFoundError("Expense was not found.")
    return expense


def _get_project(session: Session, project_id: int) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project was not found.")
    return project


def _ensure_category_exists(session: Session, category_id: int | None) -> None:
    if category_id is not None and session.get(ExpenseCategory, category_id) is None:
        raise NotFoundError("Expense category was not found.")


def _resolve_total(qty: Decimal, unit_cost: Decimal, total: Decimal | None) -> Decimal:
    return money(total if total is not None else qty * unit_cost)


def _resolve_reimbursement_status(billable: bool, reimbursable: bool) -> str:
    if billable and reimbursable:
        return BillingStatus.UNBILLED.value
    return BillingStatus.NON_BILLABLE.value


def _ensure_expense_editable(expense: Expense) -> None:
    if expense.invoice_id is not None or expense.reimbursement_status in {
        BillingStatus.DRAFTED.value,
        BillingStatus.INVOICED.value,
    }:
        raise ConflictError("Expense is linked to an invoice and cannot be edited.")
