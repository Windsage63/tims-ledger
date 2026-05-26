from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel


class CustomerBalanceRead(BaseModel):
    customer_id: int
    open_ar: Decimal
    unapplied_credits: Decimal
    net_balance: Decimal
    open_invoice_count: int
    unapplied_payment_count: int


class ArAgingCustomerRead(BaseModel):
    customer_id: int
    customer_name: str
    current: Decimal
    days_1_30: Decimal
    days_31_60: Decimal
    days_61_90: Decimal
    days_over_90: Decimal
    total: Decimal


class ArAgingRead(BaseModel):
    as_of_date: date_type
    customers: list[ArAgingCustomerRead]
    total: Decimal
