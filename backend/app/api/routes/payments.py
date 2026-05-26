from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import ConflictError, NotFoundError
from app.db.session import get_session
from app.models import Customer, Payment, PaymentApplication
from app.schemas.payments import (
    PaymentApplicationRead,
    PaymentApplicationsCreate,
    PaymentCreate,
    PaymentRead,
)
from app.services import AccountingError, PaymentApplicationInput, apply_payment, money

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=list[PaymentRead])
def list_payments(
    session: Annotated[Session, Depends(get_session)],
    customer_id: int | None = None,
    unapplied_only: bool = False,
    payment_type: Annotated[str | None, Query(max_length=40)] = None,
) -> list[Payment]:
    query = select(Payment).order_by(Payment.payment_date.desc(), Payment.id.desc())
    if customer_id is not None:
        query = query.where(Payment.customer_id == customer_id)
    if unapplied_only:
        query = query.where(Payment.unapplied_amount > 0)
    if payment_type:
        query = query.where(Payment.payment_type == payment_type)
    return list(session.scalars(query))


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Payment:
    if session.get(Customer, payload.customer_id) is None:
        raise NotFoundError("Customer was not found.")
    amount = money(payload.amount_received)
    payment = Payment(
        **payload.model_dump(exclude={"amount_received"}),
        amount_received=amount,
        unapplied_amount=amount,
    )
    session.add(payment)
    session.commit()
    session.refresh(payment)
    return payment


@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment(
    payment_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> Payment:
    return _get_payment(session, payment_id)


@router.post("/{payment_id}/applications", response_model=list[PaymentApplicationRead])
def apply_payment_route(
    payment_id: int,
    payload: PaymentApplicationsCreate,
    session: Annotated[Session, Depends(get_session)],
) -> list[PaymentApplication]:
    try:
        payment = apply_payment(
            session,
            payment_id=payment_id,
            application_date=payload.application_date,
            applications=[
                PaymentApplicationInput(
                    invoice_id=item.invoice_id,
                    amount=item.amount,
                    notes=item.notes,
                )
                for item in payload.applications
            ],
        )
    except AccountingError as exc:
        session.rollback()
        message = str(exc)
        if message in {"Payment was not found.", "Invoice was not found."}:
            raise NotFoundError(message) from exc
        raise ConflictError(message) from exc

    session.commit()
    return list(payment.applications)


def _get_payment(session: Session, payment_id: int) -> Payment:
    payment = session.get(Payment, payment_id)
    if payment is None:
        raise NotFoundError("Payment was not found.")
    return payment
