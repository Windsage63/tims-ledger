# Core Workflows

This document is a companion reference to the primary PRD in `docs/tims_ledger_prd.md`. When wording differs, the PRD and later explicit product decisions take precedence.

## 1. User Maintains Company Profile

1. User opens Settings from the bottom of the sidebar menu and edits the Company profile.
2. User enters the company name, street address, city, state, ZIP code, email, and phone.
3. System stores a single company profile record used as invoice identity source data.
4. Newly saved or printed invoice documents use the current company profile for the invoice header and check-payable footer.
5. Existing generated invoice HTML documents are historical files and are not retroactively rewritten when the Company profile changes.

## 2. User Enters Customer

1. User creates a customer master record before entering project work, or enables Edit Mode to update an existing customer.
2. User enters customer name, street address, city, state, ZIP code, contact name, email, and phone.
3. System validates that the customer record is complete enough for project setup, invoice printing, and payment receipt.
4. System stores the customer record in the `customers` table.
5. Customer record becomes available for project creation, invoice generation, payment receipt, and derived balance reporting.

## 3. User Enters Project

1. User creates a project under an existing customer.
2. User enters `project_number`, customer, project description, and project default rate.
3. System provisions built-in rates from the default rate: `ST` at 1.0x, `OT` at 1.5x, and `TT` at 0.5x.
4. User may add custom project rates as rate code plus hourly-equivalent rate.
5. If the project needs fixed-fee billing, the fixed fee is represented by a custom project rate that will later be used on a one-hour time entry.
6. System validates that `project_number` is unique and that the project is linked to exactly one customer.
7. System stores the project record and its rate records.
8. Project becomes available for time entry, expense entry, invoice building, and payment reporting.

## 4. User Enters Time

1. User enters the work date in the entry form above the time ledger. The form stays before the list at every screen width, so adding rows does not push it below the ledger.
2. User selects the project from a dropdown showing project number and project description. The system derives the customer and available rates from the project.
3. User enters work description, duration, and rate code. There is no separate time billable toggle. Time with a selected rate of `0` is non-billable.
4. System stores the time entry as a source record, snapshots the selected rate, and calculates the line total.
5. Invoice linkage is empty until Save/Print succeeds for an invoice that includes the time entry.
6. Unbilled time with a non-zero rate is eligible for invoice building. In the invoice editor, checking or unchecking time is browser-local until Save/Print. When Save/Print succeeds, checked time entries are stamped to the invoice and unchecked prior entries have their invoice linkage cleared.
7. Fixed-fee billing is represented by a one-hour time entry that uses a custom rate equal to the fixed fee. There are no separate manual invoice lines.

## 5. User Enters Expense

1. User enters the expense date in the entry form above the expense ledger. The form stays before the list at every screen width, so adding rows does not push it below the ledger.
2. User selects the project from a dropdown showing project number and project description. The system derives the customer from the project.
3. User enters vendor, description, quantity, unit cost, category, and billable flag.
4. System stores the expense as a source record and calculates the line total.
5. Invoice linkage is empty until Save/Print succeeds for an invoice that includes the expense.
6. Unbilled billable expenses are eligible for invoice building. In the invoice editor, checking or unchecking expenses is browser-local until Save/Print. When Save/Print succeeds, checked expenses are stamped to the invoice and unchecked prior expenses have their invoice linkage cleared.
7. Non-billable expenses remain available for internal cost tracking and must not appear as invoice charges.
8. Expense categories are limited to `Materials`, `Lodging`, `Airfare`, `Mileage`, `Perdiem`, `Rental Car`, `Gas`, `Parking`, `Tolls`, `Meals`, `Entertainment`, `Gifts`, `Freight`, and `Misc.`.

## 6. User Creates Or Edits An Invoice

1. User enters or edits the invoice date, unique invoice number, project, terms, and notes. Terms default to Net 30; choices are Due on receipt and Net 10 / 15 / 30 / 45 / 60. The editor previews the calendar due date and preserves other stored terms on existing invoices. The project selector shows the project number and project description.
2. For a new invoice, the editor may hold the invoice in browser state until Save/Print. No invoice database row is required before Save/Print.
3. For an existing invoice, the system loads the saved invoice, its selected rows, eligible rows, and totals, then closes the database connection. Fields and source selections are protected until Edit Mode is enabled.
4. System lists all eligible unbilled time for the project, showing date, description, duration, rate, total, and an `invoice?` checkbox.
5. System lists all eligible unbilled expenses for the project, showing date, description, category, unit cost, total, and an `invoice?` checkbox.
6. If the project bills a fixed fee, that amount appears through the one-hour custom-rate time entry that represents the fee. There are no separate HD, non-hourly, or manual billing lines.
7. User checks and unchecks time and expense source records in the browser editor.
8. Checkbox changes update browser-side preview totals only. They do not write to the database until Save/Print.
9. Prior customer balance is shown separately from the current invoice charges. Unapplied credits may be displayed and optionally applied through payment application logic, not by rewriting invoice lines.
10. When the user clicks Save/Print, the system creates or updates the invoice, replaces all selected time and expense links, generates or overwrites the current invoice HTML, and opens the saved HTML for browser printing.
11. Checked time entries are saved with the invoice ID. Unchecked prior time entries have their invoice linkage cleared and return to the unbilled pool.
12. Checked expenses are saved with the invoice ID. Unchecked prior expenses have their invoice linkage cleared and return to the unbilled pool.
13. Existing issued invoices may be viewed and reprinted by invoice number. While protected, Print Saved Invoice opens the saved HTML without updating any invoice data, links, or documents. If the document is missing, enable Edit Mode and Save/Print to generate it. Editing and regenerating existing invoices requires Edit Mode.
14. The printed invoice shows project references as `{project number} - {project description}`.
15. The printed invoice company header and check-payable footer come from the current Company profile at Save/Print time.
16. Editing and reissuing an invoice intentionally changes accounting history. This application does not require an immutable invoice audit trail.

## 7. User Records and Applies a Payment

1. User starts a new payment draft for a customer.
2. The draft stays browser-local until the user clicks Save Payment. Drafts may begin at zero while receipt details are being entered, credits may be entered as negative payments, and the reference number may be left blank.
3. System creates or updates the persisted payment record on Save Payment with the full amount initially unapplied.
4. User applies some or all of a positive payment amount to one or more open invoices in the same editor.
5. Save Payment persists both the payment record and current invoice applications.
6. Editing payment fields, changing applications, or deleting a saved payment requires Edit Mode. Delete Payment also asks for confirmation. Discarding a modified unsaved draft asks for the shared unsaved-change confirmation.
7. System prevents over-application and updates both invoice open balances and the payment's remaining unapplied amount.
8. Customer balance shows open AR and net balance, each derived from invoices, payments, and payment applications.
9. Receive Payments shows Business totals for all records in the current database: Total Income sums saved payments, including unapplied amounts and negative corrections; Open A/R sums issued invoice balances and excludes drafts; Total Expenses sums all recorded expense line totals; Non-Billable Expenses is the portion marked non-billable and is included in Total Expenses. Search, customer, year, and status filters affect only the payment list. Totals refresh when the screen loads and after payment saves/deletes, including saves that partially succeed. They represent a year's activity only when the current dataset is limited to that year; there is no automatic annual reset.
10. Payment and application saves use multiple existing requests. If a later step fails, retain the intended draft and any created payment ID, reconcile the persisted state, and allow an intentional retry without creating another payment. If a creation response is lost before an ID is known, require inspection of the saved ledger before another create attempt.

## 8. User Exports, Backs Up, Or Restores Data

1. User can download the XLSX audit export from Settings. This export is for review and audit, not disaster recovery.
2. User can create a backup from the Back up button in any page header or from Backup & Restore in Settings. Every header displays the last normal backup time.
3. System creates a ZIP backup in `app-data/backups/` named `Tims-Ledger-Backup-{date-timestamp}.zip`.
4. The backup ZIP contains `tims-ledger.db` and the saved `invoices/` directory when it exists.
5. User can keep an unlimited number of normal backups.
6. User can select a normal backup from the restore dropdown in Settings and confirm Restore Backup.
7. Before restore, system creates a safety backup of the current database and invoice documents in `app-data/backups/safety/`.
8. System restores the selected normal backup and reloads Settings to refresh the Company profile and backup list. Other pages load the restored data on their next visit.
9. Safety backups are stored separately and are not treated as normal restore candidates.

## 9. User Reviews Customer Statements

1. Home is a welcome splash screen with a ledger illustration and application title; users navigate to Customers for statement detail.
2. User selects a customer once in Customers and opens its Statement tab. Contact remains the editable master-record tab.
3. Statement shows customer identity, Open A/R, Unapplied Credit, Net Balance, generation time, issued invoice detail, and unapplied payments. It stays read-only even with Edit Mode enabled.
4. Switching detail tabs or refreshing the statement preserves a contact draft. Selecting another customer asks before discarding any modified draft. Older statement responses cannot replace the newer customer's statement.
5. New customers have no statement until saved. Customers with no invoices or with credit alone have explicit empty sections rather than another customer's default statement.

## 10. User Intentionally Edits Existing Records

1. Customers, Projects, Time, Expenses, Invoices, and Payments open with saved records protected. New records and duplicates remain editable without enabling mode.
2. User enables the header EDIT MODE button. Its red background with black lettering means existing-record editing is enabled; a normal button means protection is on.
3. Mode resets on screen changes, cached-page return, successful save/delete, and starting a new or duplicate record. Clean saved-record selection within one screen retains the mode.
4. Modified drafts are compared with their saved baselines. Record selection, New, Duplicate, Clear/Discard, and screen navigation ask before losing changes. Cancel keeps the values and selections intact. Browser refresh/close uses the browser's native warning, whose wording and availability are browser-controlled.
5. Turning mode off with unsaved changes asks before discarding them and restoring the saved baseline. Save failures preserve the draft and do not falsely mark it clean or relock it.
6. Search/filter changes do not overwrite the draft. Existing eligibility and validation rules continue to apply with mode enabled. Settings retains its current company/backup/export workflows.
7. This prevents accidental edits in the UI; it is not API authorization or an immutable accounting audit trail.

## 11. User Reviews Overdue Invoice Tags

1. Invoice displays use Draft, Open, Paid, and Overdue N days. The first overdue day reads Overdue 1 day.
2. Due date is the invoice calendar date plus its stored terms. Due today is Open; tomorrow is one day overdue. Draft and Paid take precedence, and issued zero-value invoices retain their existing Open treatment.
3. Tags use amber at 1–30 days, orange at 31–60, red at 61–90, and dark red at 91 or more. Exact-day text remains visible at every level.
4. The Invoice list/editor, customer statements, and payment invoice rows share the calculation. Open includes issued unpaid invoices, including overdue ones; Overdue includes every positive overdue count. The overdue balance metric uses the same rule.
5. Age-dependent displays refresh when the date changes without regenerating saved documents or replacing an editor draft.
