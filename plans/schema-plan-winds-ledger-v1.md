# Winds Ledger Schema Plan v1

## Purpose

This document turns the architecture blueprint into a concrete v1 database schema plan for Winds Ledger. It defines the proposed tables, columns, data types, constraints, foreign keys, and indexes for the SQLite-backed application.

## Core Modeling Decisions

1. The database file is the single source of truth.
2. There are no manual invoice lines.
3. Fixed-fee billing is represented as a one-hour time entry using a custom project rate.
4. Money is stored as integer cents.
5. Time duration is stored as integer minutes.
6. Dates are stored as `YYYY-MM-DD` text.
7. Timestamps are stored as UTC ISO 8601 text.
8. Customer balances, invoice balances, and unapplied payment balances are derived, not stored as hand-maintained fields.

## Data Conventions

### Numeric Conventions

1. Use `INTEGER` for all money values in cents.
2. Use `INTEGER` for duration in minutes.
3. Use `REAL` for expense quantity only, because quantity may be fractional while money remains integer cents.
4. Use `INTEGER` values `0` and `1` for boolean flags in SQLite, with `CHECK` constraints.

### Text Conventions

1. Use `TEXT` for names, descriptions, notes, dates, timestamps, and enum-like fields.
2. Normalize rate codes and payment types at the application layer.

### Audit Conventions

1. Every primary business table should have `created_at` and `updated_at`.
2. Issued invoices should also store `issued_at`.
3. Payment applications should store `applied_at`.

## Table Definitions

### customers

Purpose: customer master records.

Columns:

1. `id`: `INTEGER PRIMARY KEY`
   Notes: SQLite row id alias.
2. `customer_name`: `TEXT NOT NULL`
   Notes: display and selection name.
3. `street_address`: `TEXT NOT NULL`
4. `city`: `TEXT NOT NULL`
5. `state`: `TEXT NOT NULL`
6. `zip`: `TEXT NOT NULL`
   Notes: keep as text for leading zeros.
7. `contact_name`: `TEXT NOT NULL`
8. `email`: `TEXT NOT NULL`
9. `phone`: `TEXT NOT NULL`
10. `notes`: `TEXT NULL`
11. `created_at`: `TEXT NOT NULL`
12. `updated_at`: `TEXT NOT NULL`

### projects

Purpose: project records linked to exactly one customer.

Columns:

1. `id`: `INTEGER PRIMARY KEY`
2. `project_number`: `TEXT NOT NULL UNIQUE`
   Notes: core human key.
3. `customer_id`: `INTEGER NOT NULL`
   Constraints: foreign key to `customers(id)`.
4. `description`: `TEXT NOT NULL`
5. `default_rate_cents`: `INTEGER NOT NULL CHECK (default_rate_cents >= 0)`
   Notes: ST base rate.
6. `created_at`: `TEXT NOT NULL`
7. `updated_at`: `TEXT NOT NULL`

### project_rates

Purpose: built-in and custom rates available for a project.

Design note: v1 simplifies this table to hourly-equivalent rates only. Because fixed-fee billing is represented as a one-hour time entry, a separate `rate_type` column is not required.

Columns:

1. `id`: `INTEGER PRIMARY KEY`
2. `project_id`: `INTEGER NOT NULL`
   Constraints: foreign key to `projects(id)`.
3. `rate_code`: `TEXT NOT NULL`
   Notes: `ST`, `OT`, `TT`, or custom code.
4. `rate_cents`: `INTEGER NOT NULL CHECK (rate_cents >= 0)`
5. `is_builtin`: `INTEGER NOT NULL CHECK (is_builtin IN (0,1))`
6. `sort_order`: `INTEGER NOT NULL CHECK (sort_order >= 0)`
7. `created_at`: `TEXT NOT NULL`
8. `updated_at`: `TEXT NOT NULL`

Unique constraints:

1. `UNIQUE(project_id, rate_code)`

### time_entries

Purpose: time source records whose invoice eligibility is derived from the selected rate.

Columns:

1. `id`: `INTEGER PRIMARY KEY`
2. `entry_date`: `TEXT NOT NULL`
   Notes: `YYYY-MM-DD`.
3. `project_id`: `INTEGER NOT NULL`
   Constraints: foreign key to `projects(id)`.
4. `customer_id`: `INTEGER NOT NULL`
   Constraints: foreign key to `customers(id)`.
   Notes: cached for faster filtering and reporting.
5. `description`: `TEXT NOT NULL`
6. `minutes`: `INTEGER NOT NULL CHECK (minutes > 0)`
   Notes: UI may accept decimal hours and convert.
7. `rate_code`: `TEXT NOT NULL`
   Notes: snapshot of selected rate code.
8. `rate_cents`: `INTEGER NOT NULL CHECK (rate_cents >= 0)`
   Notes: snapshot at entry time. A value of `0` means the entry is non-billable.
9. `line_total_cents`: `INTEGER NOT NULL CHECK (line_total_cents >= 0)`
   Notes: snapshot of derived value.
10. `invoice_id`: `INTEGER NULL`
   Constraints: foreign key to `invoices(id)`.
   Notes: null when unbilled.
11. `created_at`: `TEXT NOT NULL`
12. `updated_at`: `TEXT NOT NULL`

Application rule:

1. `line_total_cents` is computed as `round(minutes * rate_cents / 60)` when the entry is saved.
2. Time is invoice-eligible only when `invoice_id IS NULL` and `rate_cents > 0`.

### expenses

Purpose: expense source records.

Columns:

1. `id`: `INTEGER PRIMARY KEY`
2. `entry_date`: `TEXT NOT NULL`
   Notes: `YYYY-MM-DD`.
3. `project_id`: `INTEGER NOT NULL`
   Constraints: foreign key to `projects(id)`.
4. `customer_id`: `INTEGER NOT NULL`
   Constraints: foreign key to `customers(id)`.
   Notes: cached for faster filtering and reporting.
5. `vendor`: `TEXT NOT NULL`
6. `description`: `TEXT NOT NULL`
7. `quantity`: `REAL NOT NULL CHECK (quantity > 0)`
8. `unit_cost_cents`: `INTEGER NOT NULL CHECK (unit_cost_cents >= 0)`
9. `line_total_cents`: `INTEGER NOT NULL CHECK (line_total_cents >= 0)`
   Notes: snapshot of derived value.
10. `category`: `TEXT NOT NULL`
11. `is_billable`: `INTEGER NOT NULL CHECK (is_billable IN (0,1))`
12. `invoice_id`: `INTEGER NULL`
   Constraints: foreign key to `invoices(id)`.
   Notes: null when unbilled.
13. `created_at`: `TEXT NOT NULL`
14. `updated_at`: `TEXT NOT NULL`

Application rule:

1. `line_total_cents` is computed as `round(quantity * unit_cost_cents)` when the expense is saved.

### invoices

Purpose: invoice headers and printable document metadata.

Columns:

1. `id`: `INTEGER PRIMARY KEY`
2. `invoice_number`: `TEXT NOT NULL UNIQUE`
3. `project_id`: `INTEGER NOT NULL`
   Constraints: foreign key to `projects(id)`.
4. `customer_id`: `INTEGER NOT NULL`
   Constraints: foreign key to `customers(id)`.
5. `invoice_date`: `TEXT NOT NULL`
6. `terms_days`: `INTEGER NOT NULL CHECK (terms_days >= 0)`
   Notes: due date is derived as `invoice_date + terms_days`.
7. `po_number`: `TEXT NULL`
8. `notes`: `TEXT NULL`
9. `pdf_file_name`: `TEXT NULL`
   Notes: stored file name or relative path.
10. `issued_at`: `TEXT NULL`
   Notes: null until issued.
11. `created_at`: `TEXT NOT NULL`
12. `updated_at`: `TEXT NOT NULL`

Design note:

1. Invoice totals are not stored as hand-maintained columns in v1. They are derived from linked time and expense rows plus payment applications.

### payments

Purpose: payment and advance records.

Columns:

1. `id`: `INTEGER PRIMARY KEY`
2. `customer_id`: `INTEGER NOT NULL`
   Constraints: foreign key to `customers(id)`.
3. `payment_date`: `TEXT NOT NULL`
4. `payment_type`: `TEXT NOT NULL CHECK (payment_type IN ('payment','advance'))`
   Notes: keep v1 narrow.
5. `reference_number`: `TEXT NULL`
   Notes: check number, ACH id, or note.
6. `amount_cents`: `INTEGER NOT NULL CHECK (amount_cents > 0)`
7. `notes`: `TEXT NULL`
8. `created_at`: `TEXT NOT NULL`
9. `updated_at`: `TEXT NOT NULL`

### payment_applications

Purpose: allocations of payments to invoices.

Columns:

1. `id`: `INTEGER PRIMARY KEY`
2. `payment_id`: `INTEGER NOT NULL`
   Constraints: foreign key to `payments(id)`.
3. `invoice_id`: `INTEGER NOT NULL`
   Constraints: foreign key to `invoices(id)`.
4. `applied_amount_cents`: `INTEGER NOT NULL CHECK (applied_amount_cents > 0)`
5. `applied_at`: `TEXT NOT NULL`

Unique constraints:

1. `UNIQUE(payment_id, invoice_id)` if v1 allows only one aggregate application row per payment and invoice pair.

## Foreign Key Rules

1. `projects.customer_id -> customers.id`
2. `project_rates.project_id -> projects.id`
3. `time_entries.project_id -> projects.id`
4. `time_entries.customer_id -> customers.id`
5. `time_entries.invoice_id -> invoices.id`
6. `expenses.project_id -> projects.id`
7. `expenses.customer_id -> customers.id`
8. `expenses.invoice_id -> invoices.id`
9. `invoices.project_id -> projects.id`
10. `invoices.customer_id -> customers.id`
11. `payments.customer_id -> customers.id`
12. `payment_applications.payment_id -> payments.id`
13. `payment_applications.invoice_id -> invoices.id`

Recommended delete behavior:

1. Master tables should generally use `ON DELETE RESTRICT` in v1.
2. Child rows that represent bookkeeping history should not be cascade-deleted casually.
3. If delete support is needed in the UI, prefer business-rule validation over destructive cascades.

## Derived Values

### Invoice Amount

`invoice_amount_cents = SUM(time_entries.line_total_cents) + SUM(expenses.line_total_cents)` for all rows linked to the invoice.

### Invoice Paid Amount

`invoice_paid_cents = SUM(payment_applications.applied_amount_cents)` for the invoice.

### Invoice Open Balance

`invoice_open_cents = invoice_amount_cents - invoice_paid_cents`

### Invoice Due Date

Derived as `invoice_date + terms_days`.

### Payment Unapplied Amount

`payment_unapplied_cents = payments.amount_cents - SUM(payment_applications.applied_amount_cents)`

### Customer Open AR

Sum of open invoice balances for that customer.

### Customer Unapplied Credit

Sum of unapplied payment balances for that customer.

## Recommended Indexes

### Uniqueness Indexes

1. `UNIQUE INDEX ux_projects_project_number ON projects(project_number)`
2. `UNIQUE INDEX ux_invoices_invoice_number ON invoices(invoice_number)`
3. `UNIQUE INDEX ux_project_rates_project_rate_code ON project_rates(project_id, rate_code)`

### Foreign Key And Lookup Indexes

1. `INDEX idx_projects_customer_id ON projects(customer_id)`
2. `INDEX idx_project_rates_project_id ON project_rates(project_id)`
3. `INDEX idx_time_entries_project_date ON time_entries(project_id, entry_date)`
4. `INDEX idx_time_entries_customer_date ON time_entries(customer_id, entry_date)`
5. `INDEX idx_time_entries_invoice_id ON time_entries(invoice_id)`
6. `INDEX idx_expenses_project_date ON expenses(project_id, entry_date)`
7. `INDEX idx_expenses_customer_date ON expenses(customer_id, entry_date)`
8. `INDEX idx_expenses_invoice_id ON expenses(invoice_id)`
9. `INDEX idx_invoices_customer_date ON invoices(customer_id, invoice_date)`
10. `INDEX idx_invoices_project_date ON invoices(project_id, invoice_date)`
11. `INDEX idx_payments_customer_date ON payments(customer_id, payment_date)`
12. `INDEX idx_payment_applications_payment_id ON payment_applications(payment_id)`
13. `INDEX idx_payment_applications_invoice_id ON payment_applications(invoice_id)`

### Partial Indexes For Working Sets

1. `INDEX idx_time_entries_unbilled_nonzero_rate ON time_entries(project_id, entry_date) WHERE invoice_id IS NULL AND rate_cents > 0`
2. `INDEX idx_expenses_unbilled_billable ON expenses(project_id, entry_date) WHERE invoice_id IS NULL AND is_billable = 1`
3. `INDEX idx_invoices_customer_terms ON invoices(customer_id, invoice_date, terms_days) WHERE issued_at IS NOT NULL`

## Integrity Rules Enforced In Application Transactions

1. A time entry linked to an invoice can only be moved or unlinked through the invoice workflow.
2. An expense linked to an invoice can only be moved or unlinked through the invoice workflow.
3. Payment applications cannot exceed the payment's unapplied amount.
4. Payment applications cannot exceed the invoice's open balance.
5. Invoice issue and reissue must update PDF metadata atomically with the invoice record.

## Recommended Views Or Query Helpers

These do not need to be physical tables in v1, but the backend should provide consistent query helpers or SQL views for them.

1. `customer_balance_view`
2. `invoice_balance_view`
3. `payment_unapplied_view`
4. `unbilled_time_view`
5. `unbilled_expenses_view`

## Deliberate Simplifications In v1

1. No `invoice_lines` table.
2. No separate fixed-fee billing table.
3. No cached customer balance column.
4. No soft-delete columns unless later needed by the UI.
5. No multi-currency support.

## Open Schema Questions

1. Should `customer_name` be globally unique, or only treated as a display field.
2. Should `customer_id` remain cached on time and expense rows, or be removed in favor of joins only.
3. Should payment types stay limited to `payment` and `advance` in v1, or should `refund` be modeled from the start.
4. Should invoice PDFs be tracked by a relative file path, file name, or generated artifact identifier.
