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
5. Invoice linkage is empty until Save/Print succeeds for an invoice that includes the time entry.
6. Unbilled time with a non-zero rate is eligible for invoice building. In the invoice editor, checking or unchecking time is browser-local until Save/Print. When Save/Print succeeds, checked time entries are stamped to the invoice and unchecked prior entries have their invoice linkage cleared.
7. Fixed-fee billing is represented by a one-hour time entry that uses a custom rate equal to the fixed fee. There are no separate manual invoice lines.

## 4. User Enters Expense

1. User enters the expense date.
2. User selects the project by project number. The system derives the customer from the project.
3. User enters vendor, description, quantity, unit cost, category, and billable flag.
4. System stores the expense as a source record and calculates the line total.
5. Invoice linkage is empty until Save/Print succeeds for an invoice that includes the expense.
6. Unbilled billable expenses are eligible for invoice building. In the invoice editor, checking or unchecking expenses is browser-local until Save/Print. When Save/Print succeeds, checked expenses are stamped to the invoice and unchecked prior expenses have their invoice linkage cleared.
7. Non-billable expenses remain available for internal cost tracking and must not appear as invoice charges.

## 5. User Creates Or Edits An Invoice

1. User enters or edits the invoice date, unique invoice number, project number, terms, PO number, and notes.
2. For a new invoice, the editor may hold the invoice in browser state until Save/Print. No invoice database row is required before Save/Print.
3. For an existing invoice, the system loads the saved invoice, its selected rows, eligible rows, and totals, then closes the database connection.
4. System lists all eligible unbilled time for the project, showing date, description, duration, rate, total, and an `invoice?` checkbox.
5. System lists all eligible unbilled expenses for the project, showing date, description, category, unit cost, total, and an `invoice?` checkbox.
6. If the project bills a fixed fee, that amount appears through the one-hour custom-rate time entry that represents the fee. There are no separate HD, non-hourly, or manual billing lines.
7. User checks and unchecks time and expense source records in the browser editor.
8. Checkbox changes update browser-side preview totals only. They do not write to the database until Save/Print.
9. Prior customer balance is shown separately from the current invoice charges. Unapplied credits may be displayed and optionally applied through payment application logic, not by rewriting invoice lines.
10. When the user clicks Save/Print, the system creates or updates the invoice, replaces all selected time and expense links, generates or overwrites the current invoice HTML, and opens the saved HTML for browser printing.
11. Checked time entries are saved with the invoice ID. Unchecked prior time entries have their invoice linkage cleared and return to the unbilled pool.
12. Checked expenses are saved with the invoice ID. Unchecked prior expenses have their invoice linkage cleared and return to the unbilled pool.
13. Existing issued invoices may be viewed, edited, saved, and reprinted by invoice number.
14. Editing and reissuing an invoice intentionally changes accounting history. This application does not require an immutable invoice audit trail.

## 6. User Records and Applies a Payment

1. User records a payment for a customer.
2. System creates a payment record with the full amount initially unapplied.
3. User applies some or all of that payment to one or more open invoices.
4. System prevents over-application and updates both invoice open balances and the payment's remaining unapplied amount.
5. Customer balance shows open AR and net balance, each derived from invoices, payments, and payment applications.
