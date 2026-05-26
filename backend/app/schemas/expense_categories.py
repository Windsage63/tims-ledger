from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExpenseCategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    default_billable: bool = True
    default_reimbursable: bool = True
    tax_category: str | None = Field(default=None, max_length=120)
    revenue_category: str | None = Field(default=None, max_length=120)
    expense_category: str | None = Field(default=None, max_length=120)


class ExpenseCategoryCreate(ExpenseCategoryBase):
    pass


class ExpenseCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    default_billable: bool | None = None
    default_reimbursable: bool | None = None
    tax_category: str | None = Field(default=None, max_length=120)
    revenue_category: str | None = Field(default=None, max_length=120)
    expense_category: str | None = Field(default=None, max_length=120)


class ExpenseCategoryRead(ExpenseCategoryBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
