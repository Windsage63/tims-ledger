from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import InvoiceStatus
from app.schemas.expenses import ExpenseRead
from app.schemas.time_entries import TimeEntryRead


class InvoiceLineRead(BaseModel):
    id: int
    invoice_id: int
    source_type: str | None
    source_id: int | None
    description: str
    qty: Decimal
    unit_price: Decimal
    amount: Decimal
    line_group: str | None
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class InvoiceRead(BaseModel):
    id: int
    invoice_no: str
    customer_id: int
    invoice_date: date_type
    sent_date: date_type | None
    due_date: date_type | None
    status: InvoiceStatus
    terms: str
    subtotal_labor: Decimal
    subtotal_expenses: Decimal
    freight: Decimal
    per_diem: Decimal
    other: Decimal
    sales_tax: Decimal
    total: Decimal
    open_balance: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceDetailRead(InvoiceRead):
    lines: list[InvoiceLineRead]


class InvoiceCreate(BaseModel):
    invoice_no: str = Field(min_length=1, max_length=80)
    customer_id: int = Field(gt=0)
    invoice_date: date_type
    time_entry_ids: list[int] = Field(default_factory=list)
    expense_ids: list[int] = Field(default_factory=list)
    due_date: date_type | None = None
    terms: str = Field(default="Due on receipt", min_length=1, max_length=100)


class InvoiceSend(BaseModel):
    sent_date: date_type


class InvoiceCandidatesRead(BaseModel):
    customer_id: int
    project_id: int | None
    time_entries: list[TimeEntryRead]
    expenses: list[ExpenseRead]
