# Application review — November 9, 2026

## Revised scope after the owner's clarification

This section supersedes the implementation priorities in the original review below. The original findings remain as a record of the inspected behavior; their original severity does not by itself define the current work plan.

| Area | Clarified policy and priority |
| --- | --- |
| Generated invoice documents | Regenerable output, so loss of the saved HTML is lower priority. The reproduced failure rolled back the invoice database change correctly; it did not corrupt the stored invoice amounts or links. Save/Print can regenerate the document from database records. |
| Invoice reductions and credits | Short payments leave the remaining invoice balance open; never reduce charges automatically to match a payment. Agreed changes to charges are made through billed time/units or expenses. Reject an invoice reduction below its allocated payments. The user must first explicitly reduce/remove allocations in Receive Payments; invoice Save/Print must never choose or change allocations. No new credit-memo subsystem is needed. |
| Already received excess cash | Excess receipts remain customer credit until resolved by charges or an application to a later invoice. Credit is the unapplied portion of the original payment and appears in a negative customer Net Balance. After a refund, the user may edit the original payment to the net amount. No separate refund ledger is required. |
| Customer changes | Editing an existing customer's address, name, or contact details retains its ID and preserves financial relationships. Moving an existing project to a different customer is outside the intended workflow. A narrow reassignment guard is sufficient; no transfer workflow is needed. Existing saved HTML retains its old address until regenerated; invoice data queries read the current customer details. |
| Project prices | One price schedule is maintained per project, with special pricing represented by custom rates. For changed pricing, create a new project even when continuing earlier work. Broader historical repricing controls are lower priority under this operating rule. |
| Invoice selection | Add a separate Select All Visible action to each time/units and expense source panel. Preserve Edit Mode checks and browser-local selection until Save/Print. No billing-period filtering is needed for the current invoice-up-to-date workflow. |
| Mixed time and item quantities | Use Hrs/Units consistently for the entry field, table heading, unbilled metric, and invoice source quantity labels. Keep the existing stored quantity/rate calculations. |
| Broader expenses | Keep tracking costs of units sold as non-billable expenses. Expand the existing category list to cover Salaries, Insurance, Payroll Taxes, and other agreed overhead categories. Category text is already stored in the existing expense model; extending the allowed list does not require a new expense subsystem. General overhead can continue using an internal project. |
| Statements and receipts | Printable statements are a future module addition. Receipt attachments, scanning, OCR, and automatic entry are deferred until basic production workflows are stable. |
| Other recommendations | Reports, bank matching, project budgets, navigation improvements, and other optional modules are not part of this stability-first follow-up merely because they appeared in the review. |

### Follow-up implementation

The narrow follow-up rejects invoice reductions below allocated payments, restricts saved-project customer reassignment in the API/UI, guards against carrying another customer's payment when moving an invoice, and adds Select All Visible in both invoice source panels, Hrs/Units labels, and Salaries/Insurance/Payroll Taxes categories. Automatic allocation release was removed after the owner's correction: allocation changes must always be explicitly chosen and saved by the user in Receive Payments. The rejection message is "a paid invoice cannot be lower than the payments allocated to it". Existing negative cash corrections also accept empty applications and remain editable. The README's stale zero-rate rule is corrected. Project pricing mechanics, statement output, and receipt automation are unchanged.

Verification: 26 backend tests and 16 frontend tests passed. Regression cases cover rejection without saved invoice/document/allocation changes, exact preservation of user-chosen allocations, manual allocation removal before zero-charge reductions, and explicit allocation changes before payment reductions. Browser verification confirmed the exact rejection message and a successful retry only after manually saving the allocation change in Receive Payments. Earlier isolated checks also covered bulk selection, project customer protection, Hrs/Units labels, and added categories. Production data was not edited.

## Summary

Tim's Ledger has a coherent core for a consulting or engineering practice: customer → project → work and expenses → invoice → payment. Its domain modules, source links, saved invoice documents, and deliberate editing controls are sensible foundations. The principal product gap is visibility and completeness beyond billing: answering what happened in a period, whether the records match actual cash movements, and how each project is doing.

The original review recorded **22 findings: 1 Blocker, 8 Major, 13 Minor, and 0 Nit**. These are the original classifications, before the scope clarification above. Product gaps are distinguished from reproducible defects below. The two Major product gaps assume this is intended to become the business's primary bookkeeping application. They are less urgent if bookkeeping happens elsewhere and this remains its billing companion.

The original review did not change application source or production data. The later, limited implementation is recorded above; production data remains untouched.

### Scope and verification

- Read the product requirements, current workflows, schema, route layer, domain logic, screen controllers, and templates.
- Walked through Home, Invoices, Receive Payments, Customers and Statement, Projects, Time, Expenses, and Settings using fictional records in an isolated database on port 8005. Checked the invoice layout at 1366 × 768 as well as the narrow companion browser.
- Ran the existing suites: **15 frontend tests and 15 backend tests passed**.
- Reproduced six additional failure scenarios with disposable in-memory databases; also reproduced the negative payment failure through the UI. Verified the time rounding difference independently in Python and JavaScript.
- Simulated an invoice document write failure to verify recovery behavior. This was fault injection, not an observed production incident.
- Stopped the review server and confirmed port 8005 was free. The pre-existing uncommitted changes were left alone.
- Compared selected features with current official Intuit documentation. QuickBooks product and plan availability varies; the recommendations below concern useful behavior rather than plan equivalence.

## Critical issues — security, correctness, and reliability

### C1. **Blocker** — A failed invoice renumbering can delete the previously saved document

**Evidence:** `backend/app/invoices.py:968–974` deletes the previous HTML file before writing the replacement. The database commits later at line 1009.

**Reproduction:** Save invoice OLD-NUMBER, change its number, and simulate an `OSError` on the new document write. Rolling back restores the original database record and original filename, but its HTML file has already been deleted. Protected reprinting then has no saved document to open.

**Smallest useful fix:** Write the replacement to a temporary file first, retain the previous document until the database and new file are safely updated, and restore filesystem state on failure. Add a failure-path test for renumbering and same-filename replacement. This preserves the existing Save/Print behavior and does not require an immutable history.

### C2. **Major** — Negative payments partially save and cannot complete the normal save flow

**Evidence:** `backend/app/payments.py:305` rejects `0 > negative_amount` during update; line 359 rejects an empty allocation total of zero against a negative payment. `frontend/js/payments.js:620` always saves applications after creating the payment.

**Reproduction:** Enter −$10 with no allocations and click Save Payment. The payment is created and Total Income decreases, then the UI reports “Applications cannot exceed the payment amount.” Updating that saved payment with the same amount also fails, even when only its notes change.

**Smallest useful fix:** Permit negative records with no positive allocations, and apply the amount-versus-allocation guard only where allocations exist. Define negative receipts as refunds or cash corrections in the UI. Longer term, save payment fields and allocations in one backend transaction so users get one reliable success or failure result.

### C3. **Major** — Reassigning an existing project can split its customer identity

**Evidence:** `backend/app/projects.py:292–329` changes `projects.customer_id` without guarding or reconciling customer references stored on time, expenses, and invoices.

**Reproduction:** Create time and an invoice for customer A, then change the project's customer to B. The project belongs to B while its time and invoice still belong to A. New entries derive B. The project now contains records attributed to two customers.

**Smallest useful fix:** Refuse customer reassignment once dependent records exist, with a clear explanation. A deliberate transfer workflow can be designed later if there is a real business need. Merely updating every historical customer ID would also require handling payments and saved documents.

### C4. **Major** — Moving a paid invoice to another customer's project retains the old customer's payment

**Evidence:** `backend/app/invoices.py:866–905` changes invoice project and customer, but does not validate existing `payment_applications`. The ordinary payment allocation endpoint enforces customer eligibility; this invoice update path bypasses that invariant.

**Reproduction:** Fully pay customer A's $125 invoice. Move that invoice to customer B's project, selecting B's eligible work. Save/Print succeeds and the invoice for B remains paid by A's payment.

**Smallest useful fix:** Block cross-customer changes while applications exist. Explain how to release those applications deliberately before changing the customer. Cover this path with a domain or route integration test.

### C5. **Major** — Reducing an invoice below its applied payments strands the excess

**Evidence:** `backend/app/invoices.py:908–934` replaces source selections without comparing the resulting charge total with applied payments. Line 596 clamps displayed invoice balance to zero, while `backend/app/payments.py:217–236` sums the raw balance view for business totals.

**Reproduction:** Pay a $250 invoice in full, then replace its selected work with $125 of work. The invoice displays Paid with a $0 balance; the payment has $0 unapplied; the business Open A/R total is −$125 when this is the only invoice. That $125 is not automatically available to apply elsewhere.

**Smallest useful fix:** Reject a reduction below applied payments. The user must explicitly reduce/remove the appropriate allocations in Receive Payments before saving the invoice reduction. Invoice saves must never automatically change allocations.

### C6. **Major** — Editing time can silently replace its saved rate

**Evidence:** `frontend/js/time.js:111–128` replaces saved rate and total with the current project rate even when rendering a protected record; line 294 uses this normalization for the editor. `backend/app/time_entries.py:215–245` resolves the current rate again on every update.

**Reproduction:** Save one hour at $125, change the project's default rate to $150, then correct only the time description. The saved amount changes from $125 to $150. The editor can already show the new rate before that save, including for a historical invoiced entry whose persisted amount remains unchanged.

**Smallest useful fix:** Display the stored snapshot for saved entries. Preserve that snapshot for descriptive edits; make repricing an explicit action or an explicitly communicated result of changing project/rate selection. Keep historical and preview amounts clearly distinguishable.

### C7. **Major** — The local application depends on an external runtime for its layout

**Evidence:** `frontend/templates/base.html:12–42` loads Tailwind from `cdn.tailwindcss.com` and relies on it to compile component styles and utility classes in the browser.

**Impact:** A fresh browser load without network access or with that CDN blocked cannot reliably render the intended interface. This is a dependency finding from source inspection; network failure was not injected in the browser review.

**Smallest useful fix:** Generate and serve the required CSS locally. The application can retain its current HTML, controllers, and visual design.

## Logic and edge cases

### L1. **Minor** — Time previews and saved amounts use different rounding

**Evidence:** `frontend/js/time.js:326` uses `Math.round`; `backend/app/time_entries.py:163` and line 221 use Python `round`.

**Reproduction:** Thirty minutes at $100.01 previews as $50.01 in JavaScript but saves as $50.00 in Python. Expenses already use explicit decimal half-up rounding.

**Suggested improvement:** Adopt one documented monetary rounding rule for time, built-in rate derivation, previews, and persisted totals. Test actual half-cent boundaries rather than only ordinary whole-dollar rates.

## Product features and workflows

### P1. **Major** — There is no practical period-reporting workspace

**Evidence:** `backend/app/payments.py:217–245` supplies lifetime totals; `frontend/templates/payments.html:17–40` explicitly labels them as all records. The page registry has no Reports screen. `backend/app/reporting.py:171` provides receivables detail, and line 254 provides whole-ledger audit sheets, rather than selectable period summaries.

**Business consequence:** “What did we collect last quarter?”, “What did we spend this year?”, and “Which customers produced the work?” require exporting and rebuilding spreadsheet analysis. A year filter on the payment ledger intentionally does not change its business totals.

**Minimum addition:** A separate Reports screen with date range, cash received, invoiced work, recorded expenses by existing category, customer/project summaries, unbilled work, and receivables aging. Keep lifetime payment metrics as they are. Label cash received separately from invoiced revenue; a receipts-minus-recorded-expenses figure should be described as an operational surplus until expense completeness and accounting treatment support a profit claim.

QuickBooks supplies period comparisons and cash/accrual reporting; Tim's Ledger can start with much smaller, clearly defined reports. [Intuit: profit and loss comparison reports](https://quickbooks.intuit.com/learn-support/en-us/help-article/report-management/run-profit-loss-comparison-report/L6GthoBhe_US_en_US).

### P2. **Major** — There is no way to confirm records against bank or card activity

**Evidence:** The schema in `migrations/0001_initial.sql` has receipts, expenses, and invoice applications, but no payment account, clearing state, bank reference matching, or reconciliation entity. The routes and screens offer no matching workflow.

**Business consequence:** A missed receipt, duplicate expense, card fee, or difference between a gross payment and net deposit has no systematic place to be resolved. This matters most if the app becomes the primary bookkeeping record.

**Minimum addition:** Begin with an account or payment-method field, statement import or manual comparison, cleared/unmatched status, and duplicate detection. Track the comparison cutoff and unmatched items. A full account reconciliation will also need starting balances and treatment of transfers; bank feeds can wait.

QuickBooks' reconciliation compares recorded activity with bank and card statements. The useful part to borrow is the checking process. [Intuit: reconcile an account](https://quickbooks.intuit.com/learn-support/en-us/help-article/statement-reconciliation/reconcile-account-quickbooks-online/L3XzsllsK_US_en_US).

### P3. **Minor** — Projects lack budget and progress visibility

**Evidence:** `backend/app/projects.py:38–44` models identity, customer, description, and rates. `frontend/templates/projects.html:16–21` emphasizes counts and average rates. There is no contract value, budget, estimate, phase, or remaining-fee model.

**Minimum addition:** An optional authorized fee and hours budget, actual labor hours where distinguishable, recorded costs, invoiced amount, unbilled amount, and budget remaining. Add estimates and milestone billing only if fixed-fee engagements make them useful. Margin needs a labor cost assumption, not just the billing rate.

QuickBooks has estimate-to-progress-invoice and project cost comparison workflows in applicable products and plans. A single budget-versus-actual panel would deliver much of the benefit here. [Intuit: progress invoices](https://quickbooks.intuit.com/learn-support/en-us/help-article/invoicing/set-send-progress-invoices-quickbooks-online/L0Ymm6WjR_US_en_US), [Intuit: project estimates versus actuals](https://quickbooks.intuit.com/learn-support/en-us/help-article/manage-projects/compare-project-cost-estimates-vs-actuals-online/L9oxsLKqN_US_en_US).

### P4. **Minor** — Noncash adjustments have no clear workflow

**Evidence:** `backend/app/payments.py:20–26` defines receipts; the schema and routes have no credit memo, discount, or write-off entity. Positive unapplied payments already support excess receipts and retainers, so those are not missing.

**Business consequence:** Waiving $100 of an invoice is different from receiving $100 or refunding $100. Using payment records for all three obscures cash totals. Negative payments alone do not represent a credit reducing the customer's debt.

**Minimum addition:** A dated adjustment with customer, optional invoice, amount, and reason that affects the receivable without pretending cash changed hands. Preserve editable invoices as an intentional product choice; an immutable audit trail is unnecessary for this improvement. [Intuit: credit memos and delayed credits](https://quickbooks.intuit.com/learn-support/en-us/help-article/customer-refunds-credits/create-apply-credit-memos-delayed-credits-online/L5kne9EiI_US_en_US).

### P5. **Minor** — Completed projects cannot be archived

**Evidence:** `backend/app/projects.py:38–44` has no lifecycle state; the project lookup feeds all projects into entry selectors. Deletion is correctly blocked when dependent records exist.

**Minimum addition:** Active/Closed status and “Show closed” filters. Keep historical projects and documents accessible, while excluding closed work from normal new-entry selections. This will matter more each year the business uses the application.

### P6. **Minor** — Several secondary accounting needs remain external

**Evidence:** `backend/app/expenses.py:34–44` has a vendor text field and project cost, but no receipt attachment, bill due date, paid/unpaid state, or staff identity. Time likewise has no worker identity. The available screens and routes have no recurring template or invoice-delivery workflow.

**Suggested priority:** Receipt attachments and vendor suggestions are small conveniences. Add unpaid vendor/subcontractor bills only if obligations are entered before payment; add worker identity only if multiple people record work; add recurring templates only for repeat retainers or expenses. Sales tax, payroll, inventory, purchase orders, and multi-currency support should depend on actual business needs. Their absence alone is not a defect in this product.

QuickBooks supports recurring invoice templates, including reminders and drafts. That pattern could be useful without automatic sending or charging. [Intuit: recurring transactions](https://quickbooks.intuit.com/learn-support/en-us/help-article/recurring-transactions/create-recurring-transactions-quickbooks-online/L3WoKX2R8_US_en_US).

### P7. **Minor** — Backups are easy to create but difficult to take elsewhere through the UI

**Evidence:** `backend/app/backups.py:48–54` stores them inside the runtime data directory; `frontend/templates/company.html:88–98` offers creation and selection of local backups plus XLSX export. There is no ZIP download, external destination selector, or backup upload/import workflow.

**Minimum addition:** “Save backup copy…” and “Restore from backup file…” with validation and the existing safety backup. Display the actual backup folder. If off-device copying is already handled by the user's backup software, this is primarily a discoverability improvement.

## UI and navigation

### U1. **Minor** — Related records are disconnected across screens

**Evidence:** The project editor is a setup/rates form. `frontend/js/customers.js:70–81` renders invoice and payment statement cards as plain text. The invoice editor shows a customer name without an account shortcut; navigation is primarily the shared sidebar.

**Observed friction:** To investigate a project, the user repeatedly opens Time, Expenses, Invoices, Payments, and Customers and reconstructs the same context.

**Minimum addition:** Contextual actions: Project → View Time / View Expenses / Create Invoice; Invoice → Receive Payment / View Customer; Statement invoice → Open Invoice. Use preselected filters and record IDs. A project overview with these actions is more valuable than adding more global menu items. Home can remain the welcome splash as specified.

### U2. **Minor** — Key ledger columns are hidden at ordinary laptop widths

**Evidence:** `frontend/templates/invoices.html:31` enables a side-by-side ledger/editor at the `xl` breakpoint while `frontend/templates/base.html:65` requires a 740px invoice table. The customer table has a 900px minimum at line 66.

**Observed friction:** At 1366 × 768, the invoice ledger requires horizontal scrolling to reveal balance and status, the fields most useful for collections. The narrow companion view additionally requires whole-page horizontal scrolling, which is consistent with the documented 1024px minimum.

**Minimum addition:** Keep invoice number, customer, balance, and status visible; put secondary information into the selected detail or combine cells. Offer full-width browse/detail views or move the split later. Preserve the dense desktop ledger design.

### U3. **Minor** — Monthly invoice preparation requires excessive row-by-row work

**Evidence:** `frontend/templates/invoices.html:160–173` and `frontend/js/invoices.js:298–307` display individual source checkboxes. `backend/app/invoices.py:636–654` makes eligible project rows available without a billing-period selector.

**Minimum addition:** Browser-local billing-period/cutoff filters, Select All Visible, Clear Visible, and counts/amounts for selected rows. Show a per-project unbilled queue. This keeps all checkbox changes local until Save/Print, preserves zero-rate eligibility, and avoids adding manual invoice lines.

### U4. **Minor** — The Edit Mode control is distant from the protected editor

**Evidence:** `frontend/templates/base.html:104` puts the shared mode button in the header, while long invoice and payment editors put actions well below it. Successful saves deliberately reset the mode.

**Minimum addition:** Add a clear “Protected — enable Edit Mode to change” message beside the selected record and a local control wired to the same protection mechanism. Keep the intentional save/reset behavior and handler guards. This improves explanation without weakening protection.

### U5. **Minor** — Customer statements are hard to deliver or use as a collections worklist

**Evidence:** `frontend/templates/customers.html:147–160` offers a narrow statement panel and Refresh, with no dedicated print/export action. The statement lists issued invoices and unapplied payments, rather than a dated transaction history or receivable aging buckets.

**Minimum addition:** Print/PDF-friendly statement output, open-only view, period/as-of date where supported, and aging buckets on Reports. Keep statement generation read-only. Email integration can remain optional; saving a clean document and marking an invoice as sent would already help.

### U6. **Minor** — Parts and fixed-fee quantities are presented as labor hours

**Evidence:** `frontend/templates/time.html:22` labels the metric Unbilled Hours; `frontend/js/time.js:185` sums every unbilled entry's minutes. The prescribed custom-rate model also stores parts quantities and fixed fees as time units, and invoice source labels append “h”.

**Reproduction:** Seven labor hours, two hardware units, one zero-priced hour, and one fixed-fee unit display as eleven unbilled hours. That is a valid source quantity total, but it is not eleven hours of labor.

**Minimum addition:** Label mixed totals as quantities, or introduce an explicit user-selected unit/type to distinguish hours, items, and fixed fees for display and reporting. Retain the underlying custom-rate workflow if desired. Do not infer a type or billability from a zero price.

## Simplification and minimalism

The module boundaries and one-controller-per-screen approach fit this application's size. I would prioritize the findings above over adopting a frontend framework, ORM, event-sourcing system, or generalized accounting engine. There is no evidenced need for a broad rewrite.

## Elegance and idiomatic enhancements

No additional style-only findings. The worthwhile implementation improvements are already attached to concrete failures: consistent monetary rounding, preservation of saved rate snapshots, validated relationship changes, and coordinated filesystem/database updates.

## Documentation and testability

### D1. **Minor** — The README contradicts the active time eligibility rule

**Evidence:** `README.md:127` says a zero rate is non-billable, while `docs/tims_ledger_prd.md:89`, current workflows, migration 0005, and frontend tests explicitly treat zero as an ordinary price with invoice eligibility.

**Suggested improvement:** Update that README sentence. Add focused tests for C1–C6 and L1 when fixing them. The existing passing suites are useful but do not establish that these cross-record save paths work; the business-summary tests insert negative payments directly and therefore miss the ordinary negative-payment save failure.

## Positive observations

- Source-linked billing avoids retyping charges and gives time and expenses a clear lifecycle.
- Applied payments are separate from receipts, allowing split allocations and unapplied retainers.
- Invoice charge totals are intentionally independent of other account balances.
- Saved-document printing correctly avoids regenerating protected invoices.
- Fractional-cent expense rates use explicit decimal arithmetic and retain their original precision.
- Shared draft protection and stale-response handling are substantial improvements over spreadsheet editing.
- Parameterized domain queries, escaped invoice text, page allowlisting, and loopback hosting are appropriate foundations for a local single-operator tool. This review is not a complete penetration test.
- ZIP backups contain both records and documents, and restore creates a safety backup.

The code does not need another framework. It needs fewer ways for a perfectly ordinary correction to become a financial mystery.

## Suggested implementation sequence

1. Correct C1–C6 and L1, with focused regression tests. Bundle the CSS locally.
2. Add Reports and contextual project/customer navigation. Keep Home and lifetime payment totals as designed.
3. Add simple statement matching and explain cash versus noncash adjustments.
4. Add project closing, budgets, billing-period selection, and printable statements.
5. Select secondary features from actual usage: receipts, recurring templates, unpaid vendor bills, staff time, or delivery tracking.

## Prioritized findings summary

Effort: Low = localized work usually under 30 minutes; Med = hours and multiple files; High = new workflow or substantial design work. Estimates are relative scope, not delivery commitments.

| ID | Severity | Section | Finding | Effort |
| --- | --- | --- | --- | --- |
| C1 | **Blocker** | Correctness | Failed renumbering deletes the saved invoice document | Med |
| C2 | **Major** | Correctness | Negative payment save fails after persistence | Med |
| C3 | **Major** | Correctness | Project customer reassignment splits record ownership | Low |
| C4 | **Major** | Correctness | Invoice customer reassignment retains another customer's payment | Low |
| C5 | **Major** | Correctness | Invoice reductions strand overpayments | Med |
| C6 | **Major** | Correctness | Time description edits silently reprice saved work | Med |
| C7 | **Major** | Reliability | Local UI depends on remote runtime CSS | Med |
| P1 | **Major** | Product | Period reporting is absent | High |
| P2 | **Major** | Product | Cash records cannot be matched/reconciled | High |
| L1 | **Minor** | Logic | Time preview and persistence round differently | Med |
| D1 | **Minor** | Documentation | README retains obsolete zero-rate rule | Low |
| P3 | **Minor** | Product | Project budgets and progress are absent | High |
| P4 | **Minor** | Product | Noncash credits and write-offs lack a workflow | High |
| P5 | **Minor** | Product | No project closing/archive state | Med |
| P6 | **Minor** | Product | Secondary accounting needs require external workflows | High |
| P7 | **Minor** | Product | Portable backup/restore actions are missing | Med |
| U1 | **Minor** | UI | Related records lack contextual shortcuts | Med |
| U2 | **Minor** | UI | Balance/status columns require horizontal scrolling | Med |
| U3 | **Minor** | UI | Invoice source selection lacks period and bulk controls | Med |
| U4 | **Minor** | UI | Protected editors do not explain editing locally | Low |
| U5 | **Minor** | UI | Statements lack clean delivery/collections views | Med |
| U6 | **Minor** | UI | Mixed source quantities are labeled as hours | Med |
