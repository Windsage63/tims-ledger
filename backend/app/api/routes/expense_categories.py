from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import ConflictError, NotFoundError
from app.db.session import get_session
from app.models import ExpenseCategory
from app.schemas.expense_categories import (
    ExpenseCategoryCreate,
    ExpenseCategoryRead,
    ExpenseCategoryUpdate,
)

router = APIRouter(prefix="/expense-categories", tags=["expense categories"])


@router.get("", response_model=list[ExpenseCategoryRead])
def list_expense_categories(
    session: Annotated[Session, Depends(get_session)],
    search: Annotated[str | None, Query(max_length=120)] = None,
) -> list[ExpenseCategory]:
    query = select(ExpenseCategory).order_by(ExpenseCategory.name)
    if search:
        query = query.where(ExpenseCategory.name.ilike(f"%{search}%"))
    return list(session.scalars(query))


@router.post("", response_model=ExpenseCategoryRead, status_code=status.HTTP_201_CREATED)
def create_expense_category(
    payload: ExpenseCategoryCreate,
    session: Annotated[Session, Depends(get_session)],
) -> ExpenseCategory:
    existing = session.scalar(select(ExpenseCategory).where(ExpenseCategory.name == payload.name))
    if existing is not None:
        raise ConflictError("Expense category name already exists.")

    category = ExpenseCategory(**payload.model_dump())
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.patch("/{category_id}", response_model=ExpenseCategoryRead)
def update_expense_category(
    category_id: int,
    payload: ExpenseCategoryUpdate,
    session: Annotated[Session, Depends(get_session)],
) -> ExpenseCategory:
    category = _get_category(session, category_id)
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        existing = session.scalar(
            select(ExpenseCategory).where(
                ExpenseCategory.name == updates["name"],
                ExpenseCategory.id != category_id,
            )
        )
        if existing is not None:
            raise ConflictError("Expense category name already exists.")

    for field, value in updates.items():
        setattr(category, field, value)

    session.commit()
    session.refresh(category)
    return category


def _get_category(session: Session, category_id: int) -> ExpenseCategory:
    category = session.get(ExpenseCategory, category_id)
    if category is None:
        raise NotFoundError("Expense category was not found.")
    return category
