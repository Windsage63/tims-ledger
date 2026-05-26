from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import BillingStatus


class TimeEntryBase(BaseModel):
    date: date_type
    project_id: int = Field(gt=0)
    description: str = Field(min_length=1)
    hours: Decimal = Field(gt=0, decimal_places=2)
    work_type: str | None = Field(default=None, max_length=100)
    rate: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    billable: bool = True


class TimeEntryCreate(TimeEntryBase):
    pass


class TimeEntryUpdate(BaseModel):
    date: date_type | None = None
    project_id: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, min_length=1)
    hours: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    work_type: str | None = Field(default=None, max_length=100)
    rate: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    billable: bool | None = None


class TimeEntryRead(TimeEntryBase):
    id: int
    customer_id: int
    rate: Decimal
    billing_status: BillingStatus
    invoice_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
