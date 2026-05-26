"""initial accounting schema

Revision ID: 202605250001
Revises:
Create Date: 2026-05-25
"""
# ruff: noqa: E501

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202605250001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def money() -> sa.Numeric:
    return sa.Numeric(12, 2)


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("billing_email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("default_terms", sa.String(length=100), nullable=False, server_default="Due on receipt"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_customers_name", "customers", ["name"])

    op.create_table(
        "files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_files_sha256", "files", ["sha256"])

    op.create_table(
        "expense_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("default_billable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("default_reimbursable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("tax_category", sa.String(length=120), nullable=True),
        sa.Column("revenue_category", sa.String(length=120), nullable=True),
        sa.Column("expense_category", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("name", name="uq_expense_categories_name"),
    )

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=120), primary_key=True),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_no", sa.String(length=80), nullable=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("contract_type", sa.String(length=40), nullable=False, server_default="time_and_materials"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("default_hourly_rate", money(), nullable=True),
        sa.Column("fixed_fee_amount", money(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_projects_customer_id", "projects", ["customer_id"])
    op.create_index("ix_projects_project_no", "projects", ["project_no"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_no", sa.String(length=80), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("sent_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("terms", sa.String(length=100), nullable=False, server_default="Due on receipt"),
        sa.Column("subtotal_labor", money(), nullable=False, server_default="0"),
        sa.Column("subtotal_expenses", money(), nullable=False, server_default="0"),
        sa.Column("freight", money(), nullable=False, server_default="0"),
        sa.Column("per_diem", money(), nullable=False, server_default="0"),
        sa.Column("other", money(), nullable=False, server_default="0"),
        sa.Column("sales_tax", money(), nullable=False, server_default="0"),
        sa.Column("total", money(), nullable=False, server_default="0"),
        sa.Column("open_balance", money(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("invoice_no", name="uq_invoices_invoice_no"),
    )
    op.create_index("ix_invoices_customer_id", "invoices", ["customer_id"])
    op.create_index("ix_invoices_invoice_date", "invoices", ["invoice_date"])
    op.create_index("ix_invoices_status", "invoices", ["status"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("deposit_date", sa.Date(), nullable=True),
        sa.Column("payment_type", sa.String(length=40), nullable=False, server_default="customer_payment"),
        sa.Column("reference_no", sa.String(length=120), nullable=True),
        sa.Column("amount_received", money(), nullable=False),
        sa.Column("unapplied_amount", money(), nullable=False),
        sa.Column("bank_account", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_payments_customer_id", "payments", ["customer_id"])
    op.create_index("ix_payments_payment_date", "payments", ["payment_date"])

    op.create_table(
        "ocr_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("file_id", sa.Integer(), sa.ForeignKey("files.id"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(length=120), nullable=True),
        sa.Column("extracted_json", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "time_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("hours", sa.Numeric(8, 2), nullable=False),
        sa.Column("work_type", sa.String(length=100), nullable=True),
        sa.Column("rate", money(), nullable=False),
        sa.Column("billable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("billing_status", sa.String(length=40), nullable=False, server_default="unbilled"),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_time_entries_customer_id", "time_entries", ["customer_id"])
    op.create_index("ix_time_entries_date", "time_entries", ["date"])
    op.create_index("ix_time_entries_invoice_id", "time_entries", ["invoice_id"])
    op.create_index("ix_time_entries_project_id", "time_entries", ["project_id"])

    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("vendor", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("qty", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("unit_cost", money(), nullable=False),
        sa.Column("total", money(), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("expense_categories.id"), nullable=True),
        sa.Column("billable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("reimbursable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("paid_by", sa.String(length=120), nullable=True),
        sa.Column("payment_method", sa.String(length=120), nullable=True),
        sa.Column("reimbursement_status", sa.String(length=40), nullable=False, server_default="unbilled"),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=True),
        sa.Column("receipt_file_id", sa.Integer(), sa.ForeignKey("files.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_expenses_customer_id", "expenses", ["customer_id"])
    op.create_index("ix_expenses_date", "expenses", ["date"])
    op.create_index("ix_expenses_invoice_id", "expenses", ["invoice_id"])
    op.create_index("ix_expenses_project_id", "expenses", ["project_id"])

    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("qty", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_price", money(), nullable=False),
        sa.Column("amount", money(), nullable=False),
        sa.Column("line_group", sa.String(length=80), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"])

    op.create_table(
        "payment_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("application_date", sa.Date(), nullable=False),
        sa.Column("amount_applied", money(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_payment_applications_invoice_id", "payment_applications", ["invoice_id"])
    op.create_index("ix_payment_applications_payment_id", "payment_applications", ["payment_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_entity", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_payment_applications_payment_id", table_name="payment_applications")
    op.drop_index("ix_payment_applications_invoice_id", table_name="payment_applications")
    op.drop_table("payment_applications")
    op.drop_index("ix_invoice_lines_invoice_id", table_name="invoice_lines")
    op.drop_table("invoice_lines")
    op.drop_index("ix_expenses_project_id", table_name="expenses")
    op.drop_index("ix_expenses_invoice_id", table_name="expenses")
    op.drop_index("ix_expenses_date", table_name="expenses")
    op.drop_index("ix_expenses_customer_id", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index("ix_time_entries_project_id", table_name="time_entries")
    op.drop_index("ix_time_entries_invoice_id", table_name="time_entries")
    op.drop_index("ix_time_entries_date", table_name="time_entries")
    op.drop_index("ix_time_entries_customer_id", table_name="time_entries")
    op.drop_table("time_entries")
    op.drop_table("ocr_jobs")
    op.drop_index("ix_payments_payment_date", table_name="payments")
    op.drop_index("ix_payments_customer_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_index("ix_invoices_invoice_date", table_name="invoices")
    op.drop_index("ix_invoices_customer_id", table_name="invoices")
    op.drop_table("invoices")
    op.drop_index("ix_projects_project_no", table_name="projects")
    op.drop_index("ix_projects_customer_id", table_name="projects")
    op.drop_table("projects")
    op.drop_table("app_settings")
    op.drop_table("expense_categories")
    op.drop_index("ix_files_sha256", table_name="files")
    op.drop_table("files")
    op.drop_index("ix_customers_name", table_name="customers")
    op.drop_table("customers")
