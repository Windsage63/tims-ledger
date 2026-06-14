# API Reference

Here is a concise route map of the current API, grouped by function.

## System / health

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

## Projects

  - GET /api/projects/bootstrap
    - Loads projects and customer lookup data for the projects screen.
  - POST /api/projects
    - Creates a new project.
  - PUT /api/projects/{project_id}
    - Updates an existing project.

## Time entries

  - GET /api/time/bootstrap
    - Loads time-entry screen data, optionally for a specific year.
  - POST /api/time-entries
    - Creates a new time entry.
  - PUT /api/time-entries/{entry_id}
    - Updates an existing time entry.

## Expenses

  - GET /api/expenses/bootstrap
    - Loads expense screen data, optionally for a specific year.
  - POST /api/expenses
    - Creates a new expense.
  - PUT /api/expenses/{expense_id}
    - Updates an existing expense.

## Invoices

  - GET /api/invoices/bootstrap
    - Loads invoice screen data, optionally for a specific year.
  - GET /api/invoices/new/editor
    - Builds a new invoice editor payload for a chosen project/date.
  - GET /api/invoices/{invoice_id}/editor
    - Loads the editor payload for an existing invoice.
  - POST /api/invoices/save-print
    - Saves an invoice and generates/marks its print document.
  - GET /api/invoices/{invoice_id}/document
    - Returns the saved invoice HTML document for display/printing.

## Payments

  - GET /api/payments/bootstrap
    - Loads payment screen data, optionally for a specific year.
  - GET /api/payments/{payment_id}/editor
    - Loads the payment editor payload for one payment.
  - POST /api/payments
    - Creates a new payment.
  - PUT /api/payments/{payment_id}
    - Updates an existing payment.
  - POST /api/payments/{payment_id}/applications
    - Replaces invoice applications for a payment.
