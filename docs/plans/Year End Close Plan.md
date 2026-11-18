# Year End Close Plan

Date: November 15, 2026

Status: Separate planning item. The user requires a year-end closing procedure and guidance against editing a closed year's books. The detailed correction policy and any software enforcement remain to be designed. No year has been closed and no lock has been implemented.

Establish an explicit procedure to review and close a calendar year, retain the final records, and continue the same ledger into the next year. Keep this work separate from the [P&L Statement Plan](P%26L%20Statement%20Plan.md).

## 1 Confirmed accounting rules

  - Income occurs when cash is received, using `payments.payment_date`, including unapplied receipts and overpayments.
  - Expenses are incurred on the date recorded on the expense entry, using `expenses.entry_date`. The save timestamp and an untracked expense paid date do not govern this report.
  - Payment applications assign existing receipts to invoices. They do not recognize income again or move its receipt date.
  - Open invoices and unapplied customer credit continue across December 31 in the same database.
  - After a year is closed, users must not edit, delete, or redate that year's financial records. Later corrections need the closing procedure's defined correction/reopening path.

The P&L can be implemented before a software closing feature. Its initial help and workflow instructions must state the closed-year rule and make clear that the application does not yet enforce a year lock.

## 2 Proposed close procedure

The following is a proposed procedure to refine in this separate work item. Do not run it or mark a year closed as part of implementing P&L.

1. **Select the year.** Identify the calendar year to close, the person completing the review, and the actual close date/time. Closing 2026 may occur in 2027; January 1 does not automatically close 2026.
2. **Complete entries and corrections.** Review receipts dated in that year against receipt records, and expenses dated in that year against the supporting records. Finish intended corrections while the year is still open.
3. **Review invoices and customer balances.** Investigate duplicate receipts, missing entries, unexpected open invoices, and unapplied credit. Unpaid invoices and legitimate customer credit are valid carryforward items; do not force them to zero to complete a close.
4. **Review the annual P&L.** Run January 1 through December 31. Reconcile Customer receipts to that year's saved payment amounts, category expenses to saved expense totals, and the result to income minus expenses. Verify that next-year receipts for old invoices remain next-year income.
5. **Retain final evidence.** Create a normal application ZIP backup through the existing backup path, retain the annual P&L PDF, and retain the XLSX audit export. Record their filenames and the year reviewed in the close record. The ZIP is the recovery backup; PDF/XLSX files are review evidence.
6. **Record the close.** Record the year, reviewer, close timestamp/timezone, reconciliation notes, and retained evidence. Decide the storage and any UI/backend close action in the design phase below. Do not infer that a year is closed merely because a backup exists.
7. **Continue the ledger.** Enter next-year activity in the same database. Keep old invoices, receipts, expenses, links, and credits. Do not wipe/reseed data, start a replacement database, duplicate receipts, or manufacture opening entries just to roll the year forward.
8. **Handle later corrections deliberately.** Follow the approved correction/reopening procedure before changing closed-year source amounts or dates. Do not silently rewrite a prior receipt to its net amount for a refund in a later year.

The audit export and customer statements reflect the saved/current state when generated. They are not automatically December 31 snapshots, particularly when a close happens after new-year activity has been recorded. Label retained files accordingly. A historical December 31 A/R or unapplied-credit reconstruction needs a separate design for application history or suitable dated snapshots; current allocation timestamps are insufficient to reconstruct all prior states.

## 3 New-year activity involving older records

Closing a year must preserve ordinary collection and customer-credit workflows.

| Activity after 2026 is closed | Required treatment |
| --- | --- |
| Receive $1,000 in January 2027 for a December 2026 invoice | Save a 2027 receipt and apply it to the existing invoice. 2027 P&L includes the receipt; 2026 P&L stays unchanged. |
| Apply a December 2026 receipt to an invoice during 2027 | Permit the allocation without changing the old receipt's amount or date. No additional 2027 receipt income. |
| Apply $200 of December 2026 overpayment credit to a 2027 invoice | Reduce available credit and that invoice's open balance. Do not create another receipt or move the old receipt date. |
| Update current invoice paid/open status after a later payment | Allow the derived balance/status to change. Closed invoice charges and prior-year P&L values remain unchanged. |
| Refund or correct a closed-year receipt in a later year | Use the correction/reopening policy to be defined. Do not edit the closed receipt's amount/date through ordinary editing. |

An allocation change is permitted only if its existing validation rules still pass and it leaves closed-year source dates, amounts, invoice charges, and customer ownership unchanged. This does not promise an immutable historical A/R statement; that is a separate reporting requirement.

## 4 Decisions and implementation work

| Item | Work to plan | Decision status |
| --- | --- | --- |
| Procedure and guidance | Define the final checklist, user instructions, and close evidence. | Separate procedure required; details proposed above. |
| Close record | Decide whether the first procedure is manual or stores a closed-through year/date and review evidence in the application. | Open. |
| Enforcement | Decide whether to ship guidance first or add backend enforcement and matching UI controls. Browser Edit Mode by itself is not a year lock. | Open; do not silently add it to P&L scope. |
| Correction/reopening | Define who intentionally reopens a year, what changes are allowed, how to retain the original close evidence, and how to mark/reissue revised reports. Decide supported later-year correction treatment where reopening is not used. | Open; must be resolved before enforcing a lock. |
| Record coverage | Map edits, creates, deletes, imports, redating, invoice Save/Print, source unlink/relink, and indirect changes that could affect closed records. Check both old and proposed dates so redating cannot bypass protection. | Required if enforcement is implemented. |
| Old-record allocations | Preserve new-year applications to old invoices and old receipt credit while protecting the old source fields. The current Save Payment flow updates a payment before replacing allocations, so a lock must accommodate a valid allocation-only action without rewriting protected fields. | Required workflow, implementation design open. |
| Backup and restore | Define how future close metadata is included in normal backups/restores, and make clear that restoring a backup replaces the whole saved dataset. Do not introduce silent restoration as a correction workflow. | Required if close metadata is added. |
| Historical balances | Decide whether final evidence suffices or users require historical A/R and credit balances as of year-end. If required, design dated snapshots/history instead of using today's allocation links. | Open and separate from receipt-based P&L math. |

If application state is chosen, use a new additive ordered migration and documented backend APIs. Enforce any lock in all relevant mutation helpers/routes as well as the UI; never rely on a browser-only toggle. Check indirect effects such as invoice deletion removing payment applications, and master-record deletion affecting links. Define the actual field/record policy before implementing broad blocks.

A close is an explicit user action performed after review. Reopening, if supported, is also explicit and retains prior close evidence. There is no automatic annual database reset or requirement to mark every invoice paid.

## 5 Work sequence

1. Finalize the procedure and resolve the open correction/enforcement decisions above.
2. Map the affected backend/frontend mutation paths and design permitted cross-year allocations.
3. If needed, specify close-state storage, endpoints, UI, backup behavior, and correction/reopening actions.
4. Implement this as a change separate from P&L, with additive migrations only where required.
5. Verify on disposable records, update `docs/workflows.md`, `docs/tims_ledger_prd.md`, `docs/API Reference.md` if routes change, and the applicable `AGENTS.md` guidance.
6. Record actual verification and any remaining limits here before calling the feature complete.

## 6 Acceptance scenarios

  - A year closes only after the explicit procedure, and remains available for reporting and document access.
  - The close does not change annual receipt/expense totals, financial source amounts/dates, open invoices, or unapplied customer credit.
  - A new-year receipt can settle an old invoice while leaving the closed-year P&L unchanged.
  - Previously received credit can be applied in the new year without new income or source-record redating.
  - The user instructions prohibit editing closed years and explain the approved correction path.
  - If enforcement is chosen, direct API calls, date changes in either direction, source link changes, imports, deletes, and invoice regeneration cannot bypass the defined policy.
  - If enforcement is chosen, browser Edit Mode cannot override it; valid allocation-only operations remain available through an intentional supported flow.
  - If reopening is chosen, corrected reports are identifiable and previous close evidence remains retained.
  - Retained reports identify the year and generation time; current-state exports are not mislabeled as historical year-end balance reports.
  - Any close metadata survives the normal backup/restore path; verification uses isolated data and leaves no agent-started server running.

This item plans a future procedure and any separately chosen enforcement. It does not close the user's books or authorize changes to production financial data.
