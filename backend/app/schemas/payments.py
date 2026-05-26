from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import PaymentType


class PaymentBase(BaseModel):
    customer_id: int = Field(gt=0)
    payment_date: date_type
    deposit_date: date_type | None = None
    payment_type: PaymentType = PaymentType.CUSTOMER_PAYMENT
    reference_no: str | None = Field(default=None, max_length=120)
    amount_received: Decimal = Field(gt=0, decimal_places=2)
    bank_account: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentRead(PaymentBase):
    id: int
    unapplied_amount: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentApplicationCreate(BaseModel):
    invoice_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, decimal_places=2)
    notes: str | None = None


class PaymentApplicationsCreate(BaseModel):
    application_date: date_type
    applications: list[PaymentApplicationCreate] = Field(min_length=1)


class PaymentApplicationRead(BaseModel):
    id: int
    payment_id: int
    invoice_id: int
    application_date: date_type
    amount_applied: Decimal
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
