# Product Requirements Document (PRD): Winds Ledger

## 1. Product Summary

Winds Ledger is a desktop-first accounting workflow for customer-based project billing. The product centers on customer master data, project setup, time entry, expense entry, invoice creation from source records, and payment application against open invoices.

This PRD is the primary product reference. The workflow document in [docs/workflows.md](workflows.md) is a companion reference, and explicit product decisions take precedence when wording differs.
Stitch uses placeholder product names such as LedgerFlow and Acme Ledger in several screens. The product should be treated as Winds Ledger.

## 2. Product Goals

1. Maintain one source of truth for customers, projects, billable time, billable expenses, invoices, payments, and payment applications.
2. Support project-centric billing where invoices are assembled from stored time and expense records rather than retyped manually.
3. Provide a polished, printable invoice experience without breaking source-record traceability.
4. Give the user clear operational visibility into unbilled work, open receivables, unapplied credits, and customer balances.
5. Keep in mind that we are replacing spreadsheets, not recreating QuickBooks or SAP.

## 3. Core Workflow Summary

1. User creates or updates a customer record.
2. User creates a project under an existing customer.
3. User enters time against the project and selects the project rate code.
4. User enters expenses against the project and flags whether each expense is billable.
5. User creates or edits an invoice by selecting eligible unbilled time and expenses.
6. Invoices are issued and kept in a ledger and applied to customer accounts.
7. User records payments and applies them to customer balances, leaving any excess receipt unapplied until it is allocated.

## 4. Core Data Model And Invariants

### 4.1 Customers

Each customer record must store, at minimum:

1. customer_name
2. customer_street_address
3. customer_city
4. customer_state
5. customer_zip
6. customer_contact
7. customer_email
8. customer_phone
Customer records must be complete enough to support project setup, invoice generation, payment receipt, and customer balance reporting. Customer balance is a derived reporting value, not a hand-maintained master field.

### 4.2 Projects

Each project:

1. belongs to exactly one customer
2. has a unique project_number
3. stores project_description
4. stores project_default_rate
5. may store project_fixed_fee
6. may store customer rates, either hourly or fixed fee.

Built-in rate behavior:

1. ST = 1.0 x project_default_rate
2. OT = 1.5 x project_default_rate
3. TT = 0.5 x project_default_rate
Projects may also store custom rate entries as rate-code, rate, and rate-type values. Fixed-fee billing is represented by a custom project rate used on a one-hour time entry rather than by manual invoice lines.

### 4.3 Time Entries

Each time entry stores:

1. date
2. project_number
3. derived customer reference
4. work description
5. hours
6. rate code
7. invoice linkage, which is empty until Save/Print succeeds for an invoice that includes the entry

There is no separate time-entry billable flag. Time with a selected rate of `0` is non-billable. Only unbilled time with a non-zero rate is eligible for invoice building. In the invoice editor, checking and unchecking time entries is browser-local until Save/Print. On Save/Print, checked time entries receive the invoice linkage and unchecked prior entries have the linkage cleared. Fixed-fee-supporting or non-billable time remains available for project tracking but must not be treated automatically as labor revenue.

### 4.4 Expense Entries

Each expense entry stores:

1. date
2. project_number
3. derived customer reference
4. vendor
5. description
6. quantity
7. unit cost
8. expense category
9. billable flag
10. invoice linkage, which is empty until Save/Print succeeds for an invoice that includes the expense

Only expenses flagged as billable are eligible for invoice building. In the invoice editor, checking and unchecking expenses is browser-local until Save/Print. On Save/Print, checked expenses receive the invoice linkage and unchecked prior expenses have the linkage cleared. Non-billable expenses remain available for internal cost tracking without being treated as invoiceable lines.

### 4.5 Invoices

Each invoice:

1. has a unique invoice number
2. is associated to a project
3. stores invoice date
4. may store due date, PO number, notes, and printable presentation metadata
5. is composed from selected time and expense source records
6. can be saved, issued, viewed, reprinted, edited, and reissued through a single Save/Print workflow

Invoice lines derived from time and expenses must remain traceable back to their source records.
Invoices do not need a draft state. New invoice creation may begin in browser state, but the database row and source-record links are created or updated only when the user clicks Save/Print. Existing invoices may be edited and reissued even though that changes accounting history; an immutable invoice audit trail is out of scope for this application.

### 4.6 Payments And Payment Applications

Payments must support:

1. ordinary payment records with unapplied balance at creation
2. full unapplied amount at creation
3. partial or full application across one or more open invoices
4. over-application prevention
5. remaining unapplied balance tracking

Customer balance reporting must be explainable from invoices, payments, and payment applications.

## 5. Functional Requirements

### 5.1 Customers Module

1. Provide customer create and edit workflows using the required customer fields.
2. Allow customers to be selected during project setup and invoice display.
3. Show customer balance information, including open AR, and net present balance.
4. The Stitch customer directory card layout is acceptable as a browse view, clicking on this should pull up the full customer modal just as used for customer entry or editing.

### 5.2 Projects Module

1. Provide a searchable projects list keyed by project_number.
2. Validate project_number uniqueness.
3. Link each project to one customer.
4. Support built-in rate codes ST, OT, TT, and custom rate entries.
5. Support project_fixed_fee workflows where time and expenses may be tracked without automatically creating billable labor lines.

### 5.3 Time Tracking Module

1. Allow time entry by date, project number, work description, hours, and rate code.
2. Do not ask the user to mark time as billable or non-billable separately; time billability is derived from the selected rate, and a rate of `0` is non-billable.
3. Derive the customer and available rates from the selected project.
4. Store invoice linkage on the time entry when Save/Print is clicked for an invoice that includes that entry, and remove that linkage when Save/Print is clicked after the entry has been unchecked.
5. Show unbilled status clearly so the user can identify invoice-eligible work.
6. The Stitch time tracking table and summary cards are usable UI references, but metrics such as total hours or billable amount are secondary to the source-entry workflow.

### 5.4 Expense Management Module

1. Expense management is a core module.
2. Allow expense entry by date, project number, vendor, description, quantity, unit cost, category, and billable flag.
3. Derive the customer from the selected project.
4. Store invoice linkage on the expense record when Save/Print is clicked for an invoice that includes that expense, and remove that linkage when Save/Print is clicked after the expense has been unchecked.
5. The Stitch expense list and modal provide a strong UI basis and should be retained with workflow-aligned fields.

### 5.5 Invoice Creation And Editing

1. Invoice creation must start with invoice date, unique invoice number, and project number.
2. The system must present eligible unbilled time for that project with checkbox selection.
3. The system must present eligible unbilled expenses for that project with checkbox selection.
4. Selecting or unselecting a line must update browser-side invoice state and preview totals.
5. Selecting or unselecting a line must not write source-record invoice linkage until Save/Print.
6. Prior customer balance must display separately from the current invoice charges.
7. Unapplied credits may be shown and optionally applied through payment application logic, not by rewriting invoice lines.
8. Save/Print must create or update the invoice, replace source-record invoice links, generate or overwrite the current invoice HTML, and open the saved HTML for browser printing.
9. Save/Print must clear invoice linkage from unchecked prior rows so those rows return to the unbilled pool and can be assigned to another invoice.
10. Editing an issued invoice must preserve the same source-linked checkbox workflow and may change accounting history.
11. The printed invoice should present time-derived charges in the upper section and expense-derived charges in a separate lower section.

The Stitch WYSIWYG invoice screen should be adapted rather than discarded:

1. Keep the printable invoice canvas, customer address display, notes area, and totals layout.
2. Replace freeform primary line entry with an Add Items action that opens a modal listing eligible unbilled time and expenses with checkboxes.
3. Group selected invoice content into a time section and an expense section rather than mixing it into a generic line-item editor.
4. Treat due date, terms, and PO number as optional metadata if the business wants them.
5. Treat tax and discount fields as optional future enhancements until tax policy is defined in the workflow.

### 5.6 Invoice Ledger

1. Provide an invoice ledger listing saved invoices with search, filtering, and row actions.
2. Support status views such as All, Paid, Pending, and Overdue.
3. Derive invoice status from issuance state, open balance, and due date where applicable.
4. Support viewing saved invoice HTML documents by invoice number.

The existing Stitch invoice ledger screen is usable with minimal structural change.

### 5.7 Payments Ledger And Application Workflow

1. Add a dedicated payments ledger screen; this is required and currently missing from the Stitch set.
2. The payments ledger must list payment records, customer, payment type, original amount, unapplied amount, and application status.
3. The user must be able to open a payment and apply or remove allocations across open invoices.
4. The user must be prevented from applying more than the remaining unapplied amount.
5. Payment applications must update invoice open balances and customer balances immediately.

### 5.8 Customer Balance And Accounts Receivable Reporting

1. Customer-level views must distinguish current invoice charges, open AR, unapplied credits, and net balance.
2. Overdue indicators may be used in the UI, but they must be derived from invoice due date and open balance rather than entered manually.
3. Summary cards, customer status chips, and invoice ledger filters are acceptable presentation elements if they remain derived views of ledger data.

## 6. Screen Strategy From Stitch

The Stitch screens are strongest when used as workflow-aware shells:

1. Keep the desktop-first, high-density layout, sidebar navigation, data tables, and modal patterns.
2. Keep the project list layout, especially the rate summary per project and project-number orientation.
3. Keep the customer directory as a browse surface, but back it with the full customer master record.
4. Keep the time tracking table, including rate code and invoice-link visibility.
5. Keep expense management as a first-class screen and modal.
6. Keep the invoice ledger screen.
7. Keep the WYSIWYG invoice layout, but route line selection through a source-record modal.
8. Add a new payments ledger and payment-application screen family to complete the workflow.

## 7. UX And Interaction Guidance

1. Optimize for desktop widths with room for dense tables and side panels.
2. Favor direct manipulation of stored records over wizard-heavy flows.
3. Make invoice linkage visible wherever time or expenses appear.
4. Use consistent ledger language across screens: unbilled, invoiced, open balance, unapplied, paid, overdue.
5. Preserve printable invoice polish without allowing the printed layout to bypass accounting rules.

## 8. Out Of Scope For Initial Delivery

These ideas may be useful later but are not part of the core workflow unless separately approved:

1. receipt OCR
2. financial reporting such as profit and loss or balance sheet reporting
3. multi-user permissions
4. bank feed integration
5. reminder sending automation
6. tax automation beyond simple configurable presentation fields

## 9. Open Decisions

1. Confirm whether due date should be optional manual entry, derived from customer terms, or both.
2. Confirm whether PO number should be invoice metadata only.
3. Confirm whether tax and discount should remain hidden until policy is defined.
4. Confirm whether `project_fixed_fee` remains a stored project field or whether fixed-fee work should be represented only through custom project rates and one-hour time entries.
5. Define whether customer directory status badges should be driven only by receivables state or also by internal lifecycle flags.
