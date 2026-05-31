# Core Workflows

This document is a companion reference to the primary PRD in `docs/winds_ledger_prd.md`. When wording differs, the PRD and later explicit product decisions take precedence.

## 1. User Enters Customer

1. User creates or updates a customer master record before entering project work.
2. User enters customer name, street address, city, state, ZIP code, contact name, email, and phone.
3. System validates that the customer record is complete enough for project setup, invoice printing, and payment receipt.
4. System stores the customer record in the `customers` table.
5. Customer record becomes available for project creation, invoice generation, payment receipt, and derived balance reporting.

## 2. User Enters Project

1. User creates a project under an existing customer.
2. User enters `project_number`, customer, project description, and project default rate.
3. System provisions built-in rates from the default rate: `ST` at 1.0x, `OT` at 1.5x, and `TT` at 0.5x.
4. User may add custom project rates as rate code plus hourly-equivalent rate.
5. If the project needs fixed-fee billing, the fixed fee is represented by a custom project rate that will later be used on a one-hour time entry.
6. System validates that `project_number` is unique and that the project is linked to exactly one customer.
7. System stores the project record and its rate records.
8. Project becomes available for time entry, expense entry, invoice building, and payment reporting.

## 3. User Enters Time

1. User enters the work date.
2. User selects the project by project number. The system derives the customer and available rates from the project.
3. User enters work description, duration, and rate code. There is no separate time billable toggle. Time with a selected rate of `0` is non-billable.
4. System stores the time entry as a source record, snapshots the selected rate, and calculates the line total.
5. Invoice linkage is empty until the time entry is selected into an invoice.
6. Unbilled time with a non-zero rate is eligible for invoice building. When selected into an invoice, the time entry is stamped to that invoice immediately. When unselected, the invoice linkage is cleared immediately.
7. Fixed-fee billing is represented by a one-hour time entry that uses a custom rate equal to the fixed fee. There are no separate manual invoice lines.

## 4. User Enters Expense

1. User enters the expense date.
2. User selects the project by project number. The system derives the customer from the project.
3. User enters vendor, description, quantity, unit cost, category, and billable flag.
4. System stores the expense as a source record and calculates the line total.
5. Invoice linkage is empty until the expense is selected into an invoice.
6. Unbilled billable expenses are eligible for invoice building. When selected into an invoice, the expense is stamped to that invoice immediately. When unselected, the invoice linkage is cleared immediately.
7. Non-billable expenses remain available for internal cost tracking and must not appear as invoice charges.

## 5. User Creates an Invoice

1. User enters the invoice date, a unique invoice number, and a project number.
2. System validates that the invoice number is unique.
3. System lists all eligible unbilled time for the project, showing date, description, duration, rate, total, and an `invoice?` checkbox.
4. System lists all eligible unbilled expenses for the project, showing date, description, category, unit cost, total, and an `invoice?` checkbox.
5. If the project bills a fixed fee, that amount appears through the one-hour custom-rate time entry that represents the fee. There are no separate HD, non-hourly, or manual billing lines.
6. User selects the time and expense source records to assign to the invoice.
7. As each source record is selected, the system stamps that record to the invoice immediately and recalculates invoice totals.
8. Prior customer balance is shown separately from the current invoice charges. Unapplied credits may be displayed and optionally applied through payment application logic, not by rewriting invoice lines.
9. User may review, add, or remove eligible source records. Removing a selected record clears its invoice linkage immediately and returns it to the unbilled pool.
10. When the user issues the invoice, the system updates the invoice listing, generates the PDF, and stores or overwrites the current invoice PDF.
11. Existing issued invoices may be viewed, printed, edited, and reissued by invoice number.
12. If the user edits an issued invoice, the same source-linked checkbox workflow applies: added records are stamped immediately, removed records are unstamped immediately, and reissuing updates the current PDF.

## 6. User Records and Applies a Payment

1. User records a payment for a customer.
2. System creates a payment record with the full amount initially unapplied.
3. User applies some or all of that payment to one or more open invoices.
4. System prevents over-application and updates both invoice open balances and the payment's remaining unapplied amount.
5. Customer balance shows open AR and net balance, each derived from invoices, payments, and payment applications.
