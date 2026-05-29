from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    INACTIVE = "inactive"


class ContractType(StrEnum):
    TIME_AND_MATERIALS = "time_and_materials"
    FIXED_FEE = "fixed_fee"
    HOURLY = "hourly"


class BillingStatus(StrEnum):
    UNBILLED = "unbilled"
    ASSIGNED = "assigned"
    DRAFTED = "drafted"
    INVOICED = "invoiced"
    VOIDED = "voided"
    NON_BILLABLE = "non_billable"


class InvoiceStatus(StrEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    SENT = "sent"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    VOID = "void"


class PaymentType(StrEnum):
    CUSTOMER_PAYMENT = "customer_payment"
    ADVANCE = "advance"
    CREDIT_ADJUSTMENT = "credit_adjustment"


class OcrJobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    FAILED = "failed"


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    billing_contact_name: Mapped[str | None] = mapped_column(String(200))
    billing_email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    billing_address_line1: Mapped[str | None] = mapped_column(String(255))
    billing_address_line2: Mapped[str | None] = mapped_column(String(255))
    billing_city: Mapped[str | None] = mapped_column(String(120))
    billing_state: Mapped[str | None] = mapped_column(String(50))
    billing_postal_code: Mapped[str | None] = mapped_column(String(30))
    default_terms: Mapped[str] = mapped_column(String(100), default="Due on receipt")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    projects: Mapped[list["Project"]] = relationship(back_populates="customer")
    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="customer")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="customer")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="customer")
    payments: Mapped[list["Payment"]] = relationship(back_populates="customer")


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_no: Mapped[str] = mapped_column(String(80), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    contract_type: Mapped[str] = mapped_column(
        String(40),
        default=ContractType.TIME_AND_MATERIALS.value,
    )
    status: Mapped[str] = mapped_column(String(40), default=ProjectStatus.ACTIVE.value)
    default_hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    fixed_fee_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    customer: Mapped[Customer] = relationship(back_populates="projects")
    time_entries: Mapped[list["TimeEntry"]] = relationship(back_populates="project")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="project")


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    default_billable: Mapped[bool] = mapped_column(Boolean, default=True)
    default_reimbursable: Mapped[bool] = mapped_column(Boolean, default=True)
    tax_category: Mapped[str | None] = mapped_column(String(120))
    revenue_category: Mapped[str | None] = mapped_column(String(120))
    expense_category: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    expenses: Mapped[list["Expense"]] = relationship(back_populates="category")


class TimeEntry(TimestampMixin, Base):
    __tablename__ = "time_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    hours: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    work_type: Mapped[str | None] = mapped_column(String(100))
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    billable: Mapped[bool] = mapped_column(Boolean, default=True)
    billing_status: Mapped[str] = mapped_column(String(40), default=BillingStatus.UNBILLED.value)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), index=True)

    project: Mapped[Project] = relationship(back_populates="time_entries")
    customer: Mapped[Customer] = relationship(back_populates="time_entries")
    invoice: Mapped["Invoice | None"] = relationship(back_populates="time_entries")


class Expense(TimestampMixin, Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    vendor: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("1.00"))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("expense_categories.id"))
    billable: Mapped[bool] = mapped_column(Boolean, default=True)
    reimbursable: Mapped[bool] = mapped_column(Boolean, default=True)
    paid_by: Mapped[str | None] = mapped_column(String(120))
    payment_method: Mapped[str | None] = mapped_column(String(120))
    reimbursement_status: Mapped[str] = mapped_column(
        String(40),
        default=BillingStatus.UNBILLED.value,
    )
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), index=True)
    receipt_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))

    project: Mapped[Project] = relationship(back_populates="expenses")
    customer: Mapped[Customer] = relationship(back_populates="expenses")
    category: Mapped[ExpenseCategory | None] = relationship(back_populates="expenses")
    invoice: Mapped["Invoice | None"] = relationship(back_populates="expenses")
    receipt_file: Mapped["File | None"] = relationship()


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_no: Mapped[str] = mapped_column(String(80), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    invoice_date: Mapped[date] = mapped_column(Date, index=True)
    sent_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), index=True, default=InvoiceStatus.DRAFT.value)
    terms: Mapped[str] = mapped_column(String(100), default="Due on receipt")
    subtotal_labor: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    subtotal_expenses: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    freight: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    per_diem: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    other: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    sales_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    open_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))

    customer: Mapped[Customer] = relationship(back_populates="invoices")
    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.sort_order",
    )
    time_entries: Mapped[list[TimeEntry]] = relationship(back_populates="invoice")
    expenses: Mapped[list[Expense]] = relationship(back_populates="invoice")
    payment_applications: Mapped[list["PaymentApplication"]] = relationship(
        back_populates="invoice",
    )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    source_type: Mapped[str | None] = mapped_column(String(40))
    source_id: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    line_group: Mapped[str | None] = mapped_column(String(80))
    sort_order: Mapped[int] = mapped_column(default=0)

    invoice: Mapped[Invoice] = relationship(back_populates="lines")


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    deposit_date: Mapped[date | None] = mapped_column(Date)
    payment_type: Mapped[str] = mapped_column(
        String(40),
        default=PaymentType.CUSTOMER_PAYMENT.value,
    )
    reference_no: Mapped[str | None] = mapped_column(String(120))
    amount_received: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unapplied_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    bank_account: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)

    customer: Mapped[Customer] = relationship(back_populates="payments")
    applications: Mapped[list["PaymentApplication"]] = relationship(back_populates="payment")


class PaymentApplication(Base):
    __tablename__ = "payment_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    application_date: Mapped[date] = mapped_column(Date)
    amount_applied: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    payment: Mapped[Payment] = relationship(back_populates="applications")
    invoice: Mapped[Invoice] = relationship(back_populates="payment_applications")


class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_type: Mapped[str] = mapped_column(String(50))
    original_name: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OcrJob(TimestampMixin, Base):
    __tablename__ = "ocr_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"))
    status: Mapped[str] = mapped_column(String(40), default=OcrJobStatus.PENDING.value)
    provider: Mapped[str | None] = mapped_column(String(120))
    extracted_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    file: Mapped[File] = relationship()


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[int] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(String(80))
    before_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
