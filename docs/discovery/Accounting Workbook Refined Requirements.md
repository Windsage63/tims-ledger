# Accounting Workbook Refined Requirements

This document incorporates the user notes added to `Accounting Workbook Improvement Plan.md` and turns them into build-ready workbook requirements.

## Core Accounting Direction

  - Accounting basis: accrual.
  - Revenue is recognized when an invoice is sent.
  - Reimbursed expenses are treated as company revenue, with related employee/owner expense reports tracked as costs.
  - The owner is treated like an employee for expense-report purposes.
  - Customer advance payments must be supported.
  - Customer account balances must be visible and reliable.
  - Invoice numbers should use the short sequential invoice number, such as `662`.
  - Project number should be a separate field in the invoice list/register.
  - The compound invoice number pattern in the old income tracker, such as `250507-0662`, should not be the primary invoice key.
  - The project-year/project-number portion, such as `250507`, can be retained as a reference or generated display field if useful.

## Highest-Priority Problem

The main current weakness is not invoice printing. The invoice template creates a usable invoice, but the workbook does not maintain a proper invoice/account record.

The new system should make it easy to answer:

  - What has been invoiced?
  - What has been sent but not paid?
  - What customer has an advance payment or credit balance?
  - What payments have been received and how were they applied?
  - Which invoices are partially paid?
  - Which invoices are overdue?
  - What is the balance by customer?
  - What is the balance by project?

## Recommended Data Model

### 1. Invoice Register

One row per invoice. This becomes the main accrual revenue record.

Recommended columns:

  - Invoice No
  - Invoice Date
  - Sent Date
  - Customer
  - Project No
  - Project Description
  - Contract Type
  - Labor Revenue
  - Reimbursed Expense Revenue
  - Freight Revenue
  - Per Diem Revenue
  - Other Revenue
  - Sales Tax
  - Invoice Total
  - Due Date
  - Status
  - Amount Applied
  - Open Balance
  - Days Outstanding
  - Notes

Status values:

  - Draft
  - Sent
  - Partially Paid
  - Paid
  - Overdue
  - Void
  - Written Off

Key formulas:

  - Labor Revenue from `Time Log` by invoice number.
  - Reimbursed Expense Revenue from billable expense rows by invoice number.
  - Invoice Total from component revenue columns.
  - Amount Applied from payment applications.
  - Open Balance equals invoice total less applied payments/credits.
  - Days Outstanding calculates only for open sent invoices.

### 2. Payments / Deposits

One row per cash receipt or customer credit.

Recommended columns:

  - Payment ID
  - Customer
  - Payment Date
  - Deposit Date
  - Payment Type
  - Check/Transaction No
  - Amount Received
  - Unapplied Amount
  - Bank Account
  - Notes

Payment Type values:

  - Invoice Payment
  - Advance Payment
  - Retainer
  - Refund
  - Adjustment
  - Write-off

This table should allow payments that are not tied to an invoice yet. Those amounts become unapplied customer credits.

### 3. Payment Applications

One row per application of a payment to an invoice.

Recommended columns:

  - Application ID
  - Payment ID
  - Customer
  - Invoice No
  - Application Date
  - Amount Applied
  - Notes

Why this separate table matters:

  - One payment can pay multiple invoices.
  - One invoice can be paid by multiple payments.
  - Advance payments can sit unapplied until a later invoice is sent.
  - Customer balance can be calculated cleanly.

### 4. Customer Account Ledger

Formula-driven report, not manual entry.

Recommended columns:

  - Date
  - Customer
  - Transaction Type
  - Invoice No
  - Payment ID
  - Debit
  - Credit
  - Running Customer Balance
  - Notes

Suggested convention:

  - Invoices increase accounts receivable.
  - Payments and credits reduce accounts receivable.
  - Advance payments create customer credit until applied.

The dashboard should show both:

  - Accounts receivable by customer.
  - Unapplied customer credits by customer.

## Time Log Requirements

The existing blank formula rows are intentional and should remain acceptable. Reports should simply ignore inactive rows.

Add or calculate:

  - Active Row flag.
  - Billable Y/N.
  - Invoice No.
  - Billing Status.
  - Rate Source.
  - Formula check for Hours x Rate = Total.

Active Row should be true when a row has meaningful entered data such as date, project number, work description, hours, or invoice number.

## Expense Log Requirements

The existing expense sheet was designed for invoicing. It needs added accounting fields while preserving its invoicing function.

Recommended added fields:

  - Vendor
  - Expense Category
  - IRS/Tax Category
  - Billable to Customer Y/N
  - Reimbursable Y/N
  - Paid By
  - Employee/Owner
  - Payment Method
  - Receipt Attached Y/N
  - Receipt/File Link
  - Expense Report No
  - Invoice No
  - Reimbursement Status
  - Active Row flag

Recommended operational categories:

  - Airfare
  - Freight
  - Gifts
  - Lodging
  - Meals/Entertainment
  - Mileage
  - Per Diem
  - Rental Car
  - Fuel
  - Parking/Tolls
  - Supplies/Materials
  - Project Materials - Billable
  - Project Materials - Fixed Price / Not Separately Billed
  - Subcontractor
  - Software/Office
  - Miscellaneous

Tax categories should be handled through a configurable mapping table, reviewed by the accountant. This avoids hard-coding tax treatment into day-to-day data entry.

## Category Mapping Table

Add a `Categories` or `Accounting Setup` sheet with:

  - Operational Category
  - Default Billable Y/N
  - Default Reimbursable Y/N
  - Default IRS/Tax Category
  - Default Revenue Category
  - Default Expense Category
  - Notes

This lets the user choose business-friendly categories while still supporting year-end tax/accounting exports.

## Customer Balance Logic

Customer balance should not rely on one running-balance column in the income sheet.

Recommended calculations:

  - Total sent invoices by customer.
  - Total payments received by customer.
  - Total payments applied to invoices by customer.
  - Total unapplied advance payments by customer.
  - Open AR by customer.
  - Net customer balance.

Example interpretation:

  - Customer owes company: positive AR balance.
  - Company holds customer advance/credit: unapplied credit balance.

## Checks Sheet Requirements

Required checks:

  - Every sent invoice has customer, project number, invoice date, due date, and invoice total.
  - Invoice total equals labor revenue plus reimbursed expense revenue plus other revenue plus tax.
  - Time log invoice totals equal invoice register labor revenue.
  - Expense log billable invoice totals equal invoice register expense revenue.
  - Applied payments never exceed payment amount.
  - Applied payments never exceed invoice open balance unless explicitly allowed as credit/adjustment.
  - Paid invoices have zero open balance.
  - Partially paid invoices have positive open balance and positive amount applied.
  - Advance payments are visible as unapplied credits until applied.
  - Customer ledger total ties to invoice register and payments tables.
  - Active expense rows have category, paid-by, and reimbursable/billable status.
  - Active time rows have project, type, hours, rate, and total.

## Dashboard Requirements

Dashboard should show:

  - YTD sent invoices.
  - YTD consulting revenue.
  - YTD reimbursed expense revenue.
  - YTD freight/per diem/other revenue.
  - YTD expenses by category.
  - Open AR.
  - Overdue AR.
  - Unapplied customer advances.
  - Customer balances.
  - Unbilled time.
  - Unbilled billable expenses.
  - Revenue by project.
  - Revenue by customer.

## Implementation Priority

### Phase 1

  - Add invoice register.
  - Add payments/deposits table.
  - Add payment applications table.
  - Add customer balance report.
  - Add checks sheet.

### Phase 2

  - Add accounting fields to expense log.
  - Add category mapping table.
  - Add active-row flags.
  - Add validations and conditional formatting.

### Phase 3

  - Add dashboard and AR aging.
  - Add monthly accrual revenue report.
  - Add cash received report.
  - Add tax/bookkeeping export.

### Phase 4

  - Make the invoice template pull from the invoice register.
  - Preserve simple invoice number as the invoice key.
  - Add optional generated display/reference field for project-year/project-number if useful.

## Open Design Questions

  - Should advance payments be allowed at the customer level only, or also tied to a specific project before invoicing?
  - Should an invoice be allowed to include multiple projects, or should each invoice belong to one project?
  - Should fixed-price project material costs appear on customer invoices, or only in internal project profitability?
  - Should employee/owner expense reports be tracked in this workbook, or summarized from a separate expense-report workbook?
  - What standard payment terms should be used by default, such as Net 30?
