# Accounting Workbook Improvement Plan

Source workbook reviewed: `C:\Users\tmall\Downloads\Timesheet Log and Project Tracking 2025.xlsx`

## Current Workbook Snapshot

The workbook has six sheets:

  - `Invoice`: printable invoice template, driven by invoice number and filtered time/expense logs.
  - `Customers`: customer master list.
  - `Projects`: project master list with rate setup for straight time, overtime, travel time, and fixed fee.
  - `Time Log`: source table for billable time.
  - `Expense Log`: source table for reimbursable/project expenses.
  - `Income Tracking`: invoice and payment tracking with running balance and paid status.

The workbook already has a strong foundation: source tables, structured formulas, project/customer lookups, invoice generation, and no obvious `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, or `#N/A` formula-error cells were found in the scan.

## Key Accounting Issues Found

1. Invoice numbers use two different formats.
   - `Time Log` and `Expense Log` use simple invoice numbers such as `630` through `662`.
   *user: These are sequential invoice numbers and are use on the invoices.*
   - `Income Tracking` uses compound invoice numbers such as `250507-0662`.
   *user: The first part of these `250507` is the year a project begins and the project number i.e., 25=2025, 0507= project 507*
   - The suffix ties out cleanly for nearly all current invoices, but the workbook does not make that reconciliation explicit.

2. Invoice `639` appears mismatched.
*user: I'm not sure what happened here but let's oncentrate on the application itself and I'll check these numbers later*
   - Logs show only `$35.21` of expense tied to invoice `639`.
   - `Income Tracking` shows `$679.25` for invoice suffix `639`.
   - Difference: `$644.04`.

3. Income tracking mixes invoice totals, payments/deposits, and running-balance logic.
*user: This is a primary issue. We sometimes recieve advance payments from customers and we have issues tracking balances per customer.*
   - `Income Tracking` includes normal invoices, a beginning balance, and check/payment entries.
   - This can work, but it makes accounts receivable hard to audit unless invoices and payments are separated or clearly typed.

4. Paid status is incomplete as an accounting control.
*user: These are valid issues.*
   - Paid rows show `Y`, but there is no consistent visible status for unpaid, partially paid, written off, or adjusted invoices.
   - Payment/deposit dates are mostly blank in the sampled rows, which makes cash timing and AR aging difficult.

5. Time and expense logs include many blank future/formula rows.
*user: The spreadsheet was made with many blank rows so that the formulas could be pre-installed and the user could simply type in data without having to add rows when data was added.*
   - `Time Log`: 282 table rows, with 212 numeric time totals and 71 rows missing invoice/project.
   - `Expense Log`: 312 table rows, with 235 rows missing invoice/project.
   - Some of this is likely intentional template space, but reports should separate true entered records from blank formula rows.

6. Expense accounting is currently reimbursement-focused, not tax/bookkeeping-focused.
*user: This is an issue. The expense sheet was initially built specifically for invoicing perposes. Other accounting functions need to be created.*
   - Expenses are tied to invoices well enough for billing.
   - There is no separate chart-of-accounts category, vendor, payment method, receipt status, reimbursable flag, or owner-paid/company-paid distinction.

7. The invoice template is useful, but it is not a complete invoice register.
*user: The invoice provide a functional invoice, but provides no invoice record. The system does not adequately track customer accounts to provide most of this other information correctly*
   - The generated invoice pulls time and expenses, but invoice status, issue date, due date, sent date, paid date, and open balance live elsewhere or are implicit.

## Recommended Workbook Architecture

### 1. Dashboard

Purpose: quick answer to "How is the business doing?"

Functions:

  - Year-to-date invoiced revenue.
  - Year-to-date consulting income.
  - Year-to-date reimbursed expenses.
  - Open accounts receivable.
  - Overdue accounts receivable.
  - Unbilled time and expenses.
  - Cash received by month.
  - Revenue by customer/project.
  - Expense reimbursement by category.

Useful controls:

  - Year selector.
  - Customer selector.
  - Project selector.
  - Paid/unpaid filter.

### 2. Invoice Register

Purpose: one row per invoice, the accounting source of truth for billing and AR.

Recommended columns:

  - Invoice No
  - Full Invoice ID
  - Invoice Date
  - Customer
  - Project No
  - Project Description
  - Labor Amount
  - Reimbursable Expenses
  - Misc/Other
  - Sales Tax
  - Invoice Total
  - Due Date
  - Sent Date
  - Status
  - Amount Paid
  - Payment Date
  - Open Balance
  - Days Outstanding
  - Notes

Core formulas:

  - Labor Amount: sum from `Time Log` by invoice number.
  - Reimbursable Expenses: sum from `Expense Log` by invoice number.
  - Invoice Total: labor plus reimbursable expenses plus tax/other.
  - Amount Paid: sum from payments table by invoice number.
  - Open Balance: invoice total less payments.
  - Days Outstanding: today minus invoice date, only when unpaid.
  - Status: Draft, Sent, Paid, Partial, Overdue, Void, Write-off.

### 3. Payments / Deposits

Purpose: separate cash received from invoices issued.

Recommended columns:

  - Payment Date
  - Deposit Date
  - Customer
  - Invoice No
  - Payment Method
  - Check/Transaction No
  - Amount Received
  - Bank Account
  - Notes

Why this matters:

  - A single payment can pay one invoice, several invoices, or part of an invoice.
  - It prevents deposits/checks from being mixed into the invoice list.
  - It enables cash-basis income reporting and AR aging.

### 4. Time Log Improvements

Current columns are close. Add or refine:

  - Billable Y/N
  - Invoiced Y/N or Invoice No required when billed
  - Work Type validation: ST, OT, TT, Fixed Fee, Admin, Nonbillable
  - Billing Status: Unbilled, Drafted, Invoiced, Paid
  - Rate Source: Project Rate, Override, Fixed Fee
  - Check formula: Hours x Rate equals Total

Recommended controls:

  - Highlight rows with hours but no project.
  - Highlight billable rows with no invoice number once invoice status is Sent/Paid.
  - Separate true blank template rows from active data rows in summaries.

### 5. Expense Log Improvements

Add accounting fields:

  - Vendor
  - Expense Category / Chart of Accounts
  - Reimbursable Y/N
  - Billable to Customer Y/N
  - Paid By: Company, Owner, Customer, Other
  - Payment Method
  - Receipt Attached Y/N
  - Receipt/File Link
  - Invoice No
  - Reimbursement Status

Recommended categories:
*user: I modified this list slightly to accomodate such things as per diem as its own separate items as it is billed daily at a standardized rate, and freight that is billed. We also do not have a category for the costs of project items that are not billed directly but that might be a part of a fixed price contract.*

  - Airfare
  - Freight
  - Gifts
  - Lodging
  - Meals/Entertainment
  - Mileage
  - Per diem
  - Rental Car
  - Fuel
  - Parking/Tolls
  - Supplies/Materials
  - Subcontractor
  - Software/Office
  - Miscellaneous

### 6. Customers and Projects

Customer master improvements:

  - Customer ID
  - Billing terms
  - Default tax status
  - Default contact email
  - Active/Inactive

Project master improvements:

  - Project status: Active, Complete, Hold, Closed
  - Contract type: Hourly, Fixed Fee, Time & Expense, Internal
  - Budget/contract amount
  - Not-to-exceed amount
  - Default customer
  - Default billing terms
  - Default rates

### 7. Checks and Audit Sheet

Purpose: make accounting problems visible immediately.

Recommended checks:

  - Time log total by invoice equals invoice register labor amount.
  - Expense log total by invoice equals invoice register reimbursable expenses.
  - Invoice total equals labor plus expenses plus tax/other.
  - Payments do not exceed invoice totals unless marked as overpayment/credit.
  - Paid invoices have payment dates.
  - Unpaid invoices have open balances.
  - All active time rows have project, type, hours, rate, total.
  - All active expense rows have date, project, category, rate/amount, total.
  - All invoice numbers are unique.
  - All project numbers exist in `Projects`.
  - All customers exist in `Customers`.

### 8. Reports

Recommended reporting tabs:

  - AR Aging: Current, 1-30, 31-60, 61-90, 90+ days.
  - Monthly P&L Lite: consulting revenue, reimbursed expenses, unreimbursed expenses, net.
  - Project Profitability: labor revenue, reimbursed expenses, unreimbursed expenses, gross margin.
  - Customer Summary: invoiced, paid, open balance, average days to pay.
  - Tax/Bookkeeping Export: categorized expenses and income by month.

## Suggested Implementation Phases

### Phase 1: Stabilize Accounting Controls

  - Add an `Invoice Register`.
  - Add a `Payments` table.
  - Add a `Checks` sheet.
  - Reconcile invoice suffixes from `Income Tracking` to log invoice numbers.
  - Investigate invoice `639`.

### Phase 2: Improve Data Entry

  - Add dropdowns for customer, project, work type, expense category, reimbursable flag, paid status.
  - Add conditional formatting for missing required fields.
  - Add an active-row flag so blank template rows do not pollute reporting.

### Phase 3: Build Reporting

  - Add Dashboard.
  - Add AR aging.
  - Add monthly income and expense summaries.
  - Add project/customer profitability views.

### Phase 4: Polish Invoice Workflow

  - Make invoice generation choose from the invoice register.
  - Add due date and terms.
  - Add sent/paid/open status.
  - Optionally export or print invoice PDFs from the same template.

## Decisions To Confirm Before Rebuilding

  - Should income be tracked on cash basis, accrual basis, or both? *user: we track on an accrual basis and consider income when the invoice is sent.*
  - Are reimbursed expenses meant to be treated as revenue, pass-through reimbursement, or offset against expenses for your bookkeeping? *user: reimbursed expenses are treated as revenue at the company level and then the expense reports from the employee subtract this out as costs.  This is done because there are items that the company cannot wrtite off fully.*
  - Should owner-paid expenses be reimbursed by the company and tracked separately? *user: Owner is treated as an empoyee and provides expense reports for expenses.*
  - Do you want the workbook to match QuickBooks/tax categories, or remain a simple management tracker? *user: matching IRS tax categories would be nice. The accountant does this at the end of the year presently.*
  - Should invoice numbers continue as compound IDs like `250507-0662`, simple IDs like `662`, or both? *user: use the short number and then we will add a project number column in the invoice list.*
