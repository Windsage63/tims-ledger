from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import BillingStatus


class ExpenseBase(BaseModel):
    date: date_type
    project_id: int = Field(gt=0)
    vendor: str | None = Field(default=None, max_length=200)
    description: str = Field(min_length=1)
    qty: Decimal = Field(default=Decimal("1.00"), gt=0, decimal_places=2)
    unit_cost: Decimal = Field(ge=0, decimal_places=2)
    total: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    category_id: int | None = Field(default=None, gt=0)
    billable: bool = True
    reimbursable: bool = True
    paid_by: str | None = Field(default=None, max_length=120)
    payment_method: str | None = Field(default=None, max_length=120)


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    date: date_type | None = None
    project_id: int | None = Field(default=None, gt=0)
    vendor: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    qty: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    unit_cost: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    total: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    category_id: int | None = Field(default=None, gt=0)
    billable: bool | None = None
    reimbursable: bool | None = None
    paid_by: str | None = Field(default=None, max_length=120)
    payment_method: str | None = Field(default=None, max_length=120)


class ExpenseRead(ExpenseBase):
    id: int
    customer_id: int
    total: Decimal
    reimbursement_status: BillingStatus
    invoice_id: int | None
    receipt_file_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
