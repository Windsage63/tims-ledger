from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import ConflictError, NotFoundError
from app.db.session import get_session
from app.models import Customer
from app.schemas.customers import CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerRead])
def list_customers(
    session: Annotated[Session, Depends(get_session)],
    search: Annotated[str | None, Query(max_length=200)] = None,
    active: bool | None = None,
) -> list[Customer]:
    query = select(Customer).order_by(Customer.name)
    if search:
        query = query.where(Customer.name.ilike(f"%{search}%"))
    if active is not None:
        query = query.where(Customer.active.is_(active))
    return list(session.scalars(query))


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Customer:
    existing = session.scalar(select(Customer).where(Customer.name == payload.name))
    if existing is not None:
        raise ConflictError("Customer name already exists.")

    customer = Customer(**payload.model_dump())
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(
    customer_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> Customer:
    return _get_customer(session, customer_id)


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    session: Annotated[Session, Depends(get_session)],
) -> Customer:
    customer = _get_customer(session, customer_id)
    updates = payload.model_dump(exclude_unset=True)

    if "name" in updates:
        existing = session.scalar(
            select(Customer).where(Customer.name == updates["name"], Customer.id != customer_id)
        )
        if existing is not None:
            raise ConflictError("Customer name already exists.")

    for field, value in updates.items():
        setattr(customer, field, value)

    session.commit()
    session.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_customer(
    customer_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    customer = _get_customer(session, customer_id)
    customer.active = False
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _get_customer(session: Session, customer_id: int) -> Customer:
    customer = session.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer was not found.")
    return customer
