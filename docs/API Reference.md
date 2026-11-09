# API Reference

Here is a concise route map of the current API, grouped by function.

## System / health

  - GET /
    - Redirects to `/frontend/html/index.html`.
  - GET /frontend/html/{page_name}
    - Renders a Jinja2 screen using the shared layout. Allowed filenames are `index.html`, `customers.html`, `projects.html`, `time.html`, `expenses.html`, `invoices.html`, `payments.html`, and `company.html`.
    - Unknown filenames return HTTP 404. Page rendering supplies layout metadata only; browser controllers load business data through the existing JSON APIs.
  - GET /frontend/js/{asset_path}
    - Serves the existing JavaScript assets. Template source under `frontend/templates/` is not publicly served.
  - GET /api/health
    - Returns backend health, DB path, and migration status.
  - GET /api/system/status
    - Returns detailed system status: DB path, migrations, table/view counts, and startup state.

## Overview / reporting

  - GET /api/overview/bootstrap
    - Loads overview/dashboard data for the landing page.
  - GET /api/reports/accounts-receivable
    - Returns AR/customer receivables report data; optionally filtered by customer_id.
  - GET /api/exports/audit.xlsx
    - Downloads a human-readable audit/export workbook as an XLSX file. This is not the application backup format.

## Backups

  - GET /api/backups
    - Lists normal backup ZIP files from `app-data/backups/`.
  - POST /api/backups
    - Creates a normal backup ZIP in `app-data/backups/` named `Tims-Ledger-Backup-{date-timestamp}.zip`.
    - The ZIP contains `tims-ledger.db` and the `invoices/` document directory when it exists.
  - POST /api/backups/restore
    - Restores a selected normal backup by file name.
    - Before restore, creates a safety backup ZIP in `app-data/backups/safety/` so safety backups do not appear in the normal restore list.
    - Request body:
      - `file_name`: Backup ZIP file name from the normal backup list.

## Company

  - GET /api/company/profile
    - Loads the single Company profile used for newly generated invoice headers and check-payable footer text.
  - PUT /api/company/profile
    - Updates the single Company profile.
    - Request body:
      - `company_name`: Company name printed on invoices.
      - `street_address`: Company street address.
      - `city`: Company city.
      - `state`: Two-letter company state.
      - `zip`: Company ZIP code.
      - `email`: Company email printed on invoices.
      - `phone`: Company phone printed on invoices.
    - Existing saved invoice HTML documents are not retroactively rewritten.

## Customers

  - GET /api/customers/bootstrap
    - Loads customer list for the customers screen.
  - POST /api/customers
    - Creates a new customer.
  - PUT /api/customers/{customer_id}
    - Updates an existing customer.
  - DELETE /api/customers/{customer_id}
    - Deletes an unused customer. Returns 409 if projects, time, expenses, invoices, or payments reference the customer.

## Projects

  - GET /api/projects/bootstrap
    - Loads projects and customer lookup data for the projects screen.
  - POST /api/projects
    - Creates a new project.
  - PUT /api/projects/{project_id}
    - Updates an existing project. Its `customer_id` is fixed after creation; changing it returns 422. Customer contact/address updates use the customer endpoint and retain the same customer ID.
  - DELETE /api/projects/{project_id}
    - Deletes a project and its rates. Returns 409 if time, expenses, or invoices reference the project.

## Time entries

  - GET /api/time/bootstrap
    - Loads time-entry screen data, including project descriptions for the selector and listing, optionally for a specific year.
  - POST /api/time-entries
    - Creates a new time entry.
  - PUT /api/time-entries/{entry_id}
    - Updates an existing time entry.
  - DELETE /api/time-entries/{entry_id}
    - Deletes an unlinked time entry. Returns 409 if it belongs to an invoice; remove it from or delete the invoice first.

Time rates, including zero, are ordinary prices. Time has no billable flag. Unlinked time is eligible for invoice selection regardless of rate.

## Expenses

  - GET /api/expenses/bootstrap
    - Loads expense screen data, optionally for a specific year.
  - POST /api/expenses
    - Creates a new expense.
  - PUT /api/expenses/{expense_id}
    - Updates an existing expense.
  - DELETE /api/expenses/{expense_id}
    - Deletes an unlinked expense. Returns 409 if it belongs to an invoice; remove it from or delete the invoice first.

Expense write/read payloads use `unit_cost_ten_thousandths`, a nonnegative integer representing ten-thousandths of a dollar, instead of the former `unit_cost_cents`. For example, `$0.725` is `7250`; `$174.89` is `1748900`. Integer rates must not exceed JavaScript's safe integer limit, `9007199254740991`. Quantity must be finite and greater than zero. Calculate quantity times exact rate using decimal arithmetic, then round half up once to `line_total_cents`; `41` at `7250` returns `2973` cents. The additive precision migration multiplies existing stored cent rates by 100 without changing historical line totals or invoice links. Project/time rates and other monetary totals keep their existing cent units.

The Expenses audit sheet exports `unit_cost_ten_thousandths` and a readable numeric `unit_cost_dollars` column; the scaled integer preserves the authoritative exact value.

## Invoices

  - GET /api/invoices/bootstrap
    - Loads invoice screen data, optionally for a specific year.
  - GET /api/invoices/new/editor
    - Builds a new invoice editor payload for a chosen project/date.
  - GET /api/invoices/{invoice_id}/editor
    - Loads the editor payload for an existing invoice.
  - POST /api/invoices/save-print
    - Saves an invoice and generates/marks its print document.
    - Requires at least one selected time or expense row. Zero-dollar totals are allowed.
    - Never changes payment allocations. If selected charges total less than applied payments, returns 422 with detail "a paid invoice cannot be lower than the payments allocated to it" and leaves all saved records and the document unchanged. The user must explicitly reduce/remove allocations through Receive Payments before retrying. Cross-customer project changes are rejected while the invoice has payment applications.
    - Generated HTML has one final summary row labeled Total Invoice, equal to its time and expense charges. It omits Prior Balance, Unapplied Credit, and Total Due; payment applications do not reduce the printed charge total.
  - DELETE /api/invoices/{invoice_id}
    - Deletes the invoice and its saved document, clears its time/expense links, and removes its payment applications. Payments and other invoice applications are retained.
    - Document deletion failure retains the invoice and its links. Invalid document paths return 422.
  - GET /api/invoices/{invoice_id}/document
    - Returns the saved invoice HTML document for display/printing.
    - Read-only, including with `autoprint=1`: no document regeneration, source-link updates, or invoice changes. Existing saved HTML retains its layout until deliberate Save/Print regeneration.

New and saved invoice editor payloads, including the `editor` returned by Save/Print, have a `summary` containing exactly three integer-cent fields: `time_total_cents`, `expense_total_cents`, and `invoice_total_cents`. The summary no longer contains `prior_balance_cents`, `unapplied_credit_cents`, or `open_balance_after_issue_cents`. The invoice object's own `invoice_amount_cents`, `paid_amount_cents`, and `open_balance_cents` retain their existing meanings. Its top-level `prior_balance_cents` and `unapplied_credit_cents` remain available for compatibility with the XLSX OpenInvoices audit sheet; customer balances and statements are unchanged.

All record DELETE endpoints return 404 for missing records and an envelope with `deleted: true` and the deleted record ID on success. Saved-record delete buttons and handlers require browser-local Edit Mode and confirmation.

## Payments

  - GET /api/payments/bootstrap
    - Loads `payments` and `customers`, with the payment list optionally filtered by `year`.
    - Also returns `business_summary` with integer cent totals: `total_income_cents`, `total_open_ar_cents`, `total_expenses_cents`, and `non_billable_expenses_cents`. These totals always cover all records, even when `year` is supplied. Income sums recorded payments including unapplied amounts and negative corrections. Open A/R sums issued invoice balances, excluding drafts. Expenses sum recorded line totals; non-billable expenses are included in total expenses.
  - GET /api/payments/{payment_id}/editor
    - Loads the payment editor payload for one payment.
  - POST /api/payments
    - Creates a new payment. Payment amounts may be zero while a draft is being entered, or negative for cash corrections. The reference number is optional. Overpayments remain unapplied on the ordinary receipt and can produce a negative customer net balance; they do not change invoice charges.
    - Request body:
      - `customer_id`: Customer ID.
      - `payment_date`: Payment date as `YYYY-MM-DD`.
      - `reference_number`: Optional payment/check/reference text.
      - `amount_cents`: Payment amount in cents. Zero and negative values are allowed.
      - `notes`: Optional notes.
  - PUT /api/payments/{payment_id}
    - Updates an existing payment. The reference number is optional.
    - Uses the same request body as `POST /api/payments`.
    - Supports editing the receipt to a net amount after a refund. The amount must still cover positive applications; release allocations first when needed. Negative corrections can be updated with no positive applications.
  - DELETE /api/payments/{payment_id}
    - Deletes a payment and its invoice application rows.
  - GET /api/payments/customers/{customer_id}/open-invoices
    - Loads open invoice rows for the selected customer while editing a payment.
  - POST /api/payments/{payment_id}/applications
    - Replaces invoice applications for a payment. The payment screen calls this as part of Save Payment.
    - Zero or negative cash corrections accept an empty application list, but cannot have positive applications.
    - Request body:
      - `applications`: List of application rows.
      - Each row contains `invoice_id` and `applied_amount_cents`.
