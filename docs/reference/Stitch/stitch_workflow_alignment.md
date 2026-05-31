# Stitch Screen Alignment Matrix

This matrix records how the current Stitch screens map to the workflow in [docs/workflows.md](../../workflows.md).

| Screen | Recommendation | Notes |
| --- | --- | --- |
| accounting_suite.html | Keep as a visual shell | Useful as a general desktop layout and navigation reference. Treat the dashboard content as placeholder, not product logic. |
| projects_management.html | Keep with minor changes | Strong alignment with the workflow because it uses project number, client linkage, and displayed rate summaries. Ensure the table remains keyed by unique project_number and reflects one-customer-per-project rules. |
| new_project_modal.html | Keep and align fields | Reuse the modal structure. Keep billing rates. Ensure the form explicitly includes project_number uniqueness, customer selection, project_default_rate, project_fixed_fee, built-in rate codes, and custom rate entries. |
| customers_directory.html | Keep as browse view | The card layout is useful, but it must be backed by the full customer master record including address, contact, email, and phone. Status badges should be derived from ledger state, not manually assigned. |
| new_customer_modal.html | Keep with field expansion | Reuse the modal layout, but ensure it captures the full customer record required by the workflow. |
| time_tracking.html | Keep with workflow emphasis | Strong fit. The table already shows project, customer, description, hours, rate code, and invoice status. Keep metrics secondary to source-record accuracy. |
| new_time_entry_modal.html | Keep and simplify around workflow | Reuse the modal shell, but make project selection, rate code selection, date, description, and hours the primary fields. Any automation prompts should remain optional UI enhancements. |
| expenses_management.html | Keep as a core screen | This is not future scope. Reuse the listing, filters, and new expense action as the main expense ledger view. |
| new_expense_modal.html | Keep with workflow-aligned fields | Strong fit. Ensure billable flag and project-derived customer behavior are explicit. |
| invoice_tracking.html | Keep with minor changes | Good basis for the invoice ledger. Status tabs, search, and actions are useful. Status must be derived from issued state, open balance, and due date. |
| create_invoice.html | Adapt substantially | Keep the printable WYSIWYG canvas, totals block, notes area, and address section. Replace freeform line-entry as the primary workflow with an Add Items modal that lists eligible unbilled time and expenses with checkboxes. Allow controlled manual lines only for approved non-hourly billing. |
| payments ledger screen | Add new screen | Not present in Stitch but required by the workflow. Needs ledger listing, payment detail, and payment-application UX. |

## Reusable Concepts From Stitch

1. Desktop-first sidebar navigation and dense table layouts
2. Modal-based data entry for new customers, projects, time, and expenses
3. Project list presentation that surfaces project number and rates
4. Invoice ledger list with filters and row actions
5. Printable invoice canvas that can host a workflow-driven line selection experience

## Required Corrections To Stitch-Derived Assumptions

1. Expense management is core scope, not future scope.
2. Invoice creation cannot rely on freeform manual line entry as the primary accounting workflow.
3. The product needs a payments ledger and payment application workflow in addition to the invoice ledger.
4. Customer balances must be derived from invoices, payments, and payment applications.
5. Overdue, paid, pending, and similar badges must be derived statuses.

## Proposed Invoice UX Bridge

The best reuse path for the Stitch invoice screen is:

1. Open the WYSIWYG invoice editor.
2. Select project and invoice metadata.
3. Use Add Items to open a modal of eligible unbilled time and expenses.
4. Check or uncheck source records, stamping or unstamping them immediately.
5. Show the selected records on the invoice canvas in printable form.
6. Allow only controlled manual HD or equivalent non-hourly lines outside the source-record lists.

This preserves the polished Stitch invoice experience while keeping the workflow auditable.
