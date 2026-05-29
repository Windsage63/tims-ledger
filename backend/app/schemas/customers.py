from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    billing_contact_name: str | None = Field(default=None, max_length=200)
    billing_email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    billing_address_line1: str | None = Field(default=None, max_length=255)
    billing_address_line2: str | None = Field(default=None, max_length=255)
    billing_city: str | None = Field(default=None, max_length=120)
    billing_state: str | None = Field(default=None, max_length=50)
    billing_postal_code: str | None = Field(default=None, max_length=30)
    default_terms: str = Field(default="Due on receipt", min_length=1, max_length=100)
    active: bool = True
    notes: str | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    billing_contact_name: str | None = Field(default=None, max_length=200)
    billing_email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    billing_address_line1: str | None = Field(default=None, max_length=255)
    billing_address_line2: str | None = Field(default=None, max_length=255)
    billing_city: str | None = Field(default=None, max_length=120)
    billing_state: str | None = Field(default=None, max_length=50)
    billing_postal_code: str | None = Field(default=None, max_length=30)
    default_terms: str | None = Field(default=None, min_length=1, max_length=100)
    active: bool | None = None
    notes: str | None = None


class CustomerRead(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
