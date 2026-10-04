# Phase 2 Plan

Date: October 4, 2026

Status: Implemented and verified on October 4, 2026. Verification details follow the plan.

This phase adds protection against accidental edits, moves customer statement detail to Customers, and shows the exact number of overdue days on invoice tags. It builds on the completed [Phase 1 Plan](Phase%201%20Plan.md) and the findings in [Conversation History](Conversation%20History.md), with the decisions from our subsequent discussion taking precedence over the original recommendations.

## 1 Agreed requirements

| Area | Decision |
| --- | --- |
| Edit protection | Existing Customers, Projects, Time, Expenses, Invoices, and Payments require Edit Mode before they can be changed. |
| Header control | Show an `EDIT MODE` button. Its normal appearance means protection is on. A red background with black lettering means editing is enabled. |
| Screen changes | Reset Edit Mode when changing screens. The destination screen starts protected. |
| Unsaved changes | Warn before an action would discard unsaved changes, and let the user cancel the action. |
| Invoice editor | Keep the current editor layout and Save/Print workflow. |
| Invoice selection | Keep Time and Expenses in separate selection sections. |
| Customer statements | Move the customer statement detail and supporting customer balance information from Home to Customers. Remove the duplicate customer listing from Home. |
| Invoice status | Use Draft, Open, Paid, and Overdue with the exact number of days past terms. Do not use aging buckets as the tag text. |
| Time and Expenses layout | Keep each new entry form above its ledger listing, as already implemented. |

### Implementation defaults

The following details make the requirements concrete. They are proposed implementation choices rather than additional decisions explicitly made by the user:

- Reset Edit Mode after a successful save, a successful delete, and when starting a new or duplicate record.
- New records and duplicates can be filled in and saved without enabling Edit Mode. A duplicate has no saved record ID and cannot overwrite its source.
- Selecting another saved record on the same screen keeps the current mode, after resolving any unsaved changes. Switching screens always resets it.
- Turning Edit Mode off with unsaved changes offers a discard confirmation. Cancel keeps the draft and mode; confirm restores the saved baseline and locks the editor.
- Existing invoices can print their previously saved document while protected. Updating an invoice and regenerating its document requires Edit Mode.
- Use amber for 1 through 30 overdue days, orange for 31 through 60, red for 61 through 90, and dark red for 91 or more. The tag always includes the exact count.
- Settings is outside the six protected record screens. Company profile editing, backup, restore, and audit export retain their current workflows in this phase.

## 2 Shared edit protection

### Header behavior

Add an edit capability flag to the page registry in `backend/app/pages.py`. The shared header in `frontend/templates/base.html` renders the button on the six protected screens. Home and Settings do not show it.

Keep the label `EDIT MODE` in both states. Use `aria-pressed` to expose its state and concise help text to explain that existing records are protected until it is enabled. The red state must use black lettering with adequate contrast and a visible keyboard focus indicator. Color is accompanied by text or an accessible state description.

Store mode only in the current document's browser memory. Do not persist it in local storage, session storage, a cookie, or the database. Reset it on page initialization and when a screen is restored from the browser's back and forward cache. Do not carry it through the global New menu or a page URL.

Disable the toggle during record loading or saving. For an unsaved record, keep it off and explain that new records are already editable. Enable it when a saved record is available.

### Protected actions

| Screen | Existing data protected while mode is off | Actions still available |
| --- | --- | --- |
| Customers | Contact and address fields, notes, status, and saving changes | Browse, search, filters, statement viewing, and New Customer |
| Projects | Project fields, built-in rate inputs, custom rate fields, adding or removing custom rates, and saving | Browse, search, filters, and new or duplicate actions already supported |
| Time | Project, date, rate, units or hours, description, and saving an existing entry | Browse, filters, and new or duplicate entry actions already supported |
| Expenses | Project, date, category, amount, billability, description, and saving an existing entry | Browse, filters, and new or duplicate entry actions already supported |
| Invoices | Customer and invoice fields, terms, source-row checkboxes, and any action that updates the invoice or its source links | Browse, filters, new invoice creation, and printing the saved document |
| Payments | Customer, date, reference, amount, notes, application amounts, saving changes, and deleting a saved payment | Browse, filters, and new payment creation with allocation |

Gate any existing saved-record delete action on these screens as well as edits. Keep its delete confirmation. Do not add delete or duplicate features to screens that do not currently offer them.

Disable or make fields read-only as appropriate, and disable associated mutation controls. Also check protection in the actual event handlers and save helpers before changing draft state or sending a mutation request. Disabling a button alone is insufficient: Enter submission, delegated events, and application helpers must respect the same rule.

Existing business restrictions still apply when Edit Mode is on. Enabling it does not override source-record eligibility, invoice/payment validation, or restrictions on already invoiced work.

This is protection against accidental changes through the application UI. It is not server authorization, an audit trail, or a lock against another API client. No server-side Edit Mode session or database flag is planned.

### State transitions

| Event | Result |
| --- | --- |
| Open or return to a screen | Mode off; saved record protected |
| Enable mode on a saved record | Editor becomes editable; no mutation request is sent |
| Select another saved record with no unsaved changes | Load the record; preserve the mode within this screen |
| Select another record with unsaved changes | Confirm discard before replacing the draft; cancel leaves the current record intact |
| Start a new or duplicate record | Resolve the current draft, then enter an editable unsaved record with mode off |
| Save completes successfully | Refresh the saved baseline, mark clean, turn mode off, and protect the saved record |
| Validation or save fails | Preserve the draft; do not mark clean or reset mode as if the save succeeded |
| Turn mode off while clean | Lock the current record immediately |
| Turn mode off while dirty | Confirm discard; restore the saved baseline and lock only if confirmed |
| Navigate to another screen | Resolve unsaved changes; destination initializes with mode off |

Do not reset mode or clear dirty state in a generic `finally` block. Success, failure, and partial success need separate handling.

## 3 Draft state and unsaved changes

### Saved baseline

Each controller keeps a detached editable draft and a saved baseline. Populate both from a successful load or save response. Editing a draft must not mutate the saved object used by the browse table, status tags, or ledger metrics.

This needs particular attention in `invoices.js` and `payments.js`: their current form synchronization changes objects returned by selected-record helpers, which can reference the saved list. Separate those objects before adding cancellation or protection.

Compare the current draft with a normalized baseline rather than setting a permanent flag on the first keystroke. Changing a value and restoring it should return the editor to clean. A newly initialized blank record is clean until its values change; a prefilled duplicate is an unsaved draft that warrants a warning if abandoned.

| Screen | Include in the comparison |
| --- | --- |
| Customers | All writable customer fields, including status and notes |
| Projects | Writable project fields, built-in rates, and custom rate additions, removals, and values |
| Time | The actual time write payload, including rate and units or hours |
| Expenses | The actual expense write payload, including category and billability |
| Invoices | Writable invoice fields plus selected Time and Expense record IDs |
| Payments | Writable payment fields plus invoice application IDs and amounts |

Normalize cents, IDs, empty values, and write-payload trimming consistently. Compare invoice source selections as sets; compare payment applications by invoice ID. Preserve ordering where the application treats it as meaningful, including custom rates. Exclude filters, row selection, computed totals, loading flags, and statement data from dirty detection.

### Actions that discard a draft

Use one shared confirmation path for sidebar navigation, global New navigation, selecting another record, New, Duplicate, Clear or Discard, and reload actions that replace the editor. The same-screen `#new` path in `consumeNewRecordRequest()` must use it too.

Suggested wording: `You have unsaved changes. Continue and lose those changes?` Provide Continue and Cancel through the existing browser confirmation mechanism or an accessible equivalent.

Cancel must leave the editor values, source checkboxes, payment applications, selected record, mode, and relevant URL state intact. Confirm discards only the browser draft; it must not issue a save. Selecting the already selected record does not discard anything and should not prompt.

Search, filters, statement refresh, help, and backup do not require a warning unless they actually replace the draft. Avoid making filtered-list rerenders silently select another record. Opening a link in another tab or printing in a new window does not leave the current editor and should not warn.

Install `beforeunload` protection only while there are unsaved changes, covering refresh, tab close, and browser navigation. Browsers control the text and may require prior user interaction; custom warning text cannot be guaranteed there. App-controlled navigation uses the explicit confirmation and must avoid a second browser prompt after the user has already confirmed.

While a save is in progress, prevent app-controlled transitions that would replace its editor. Keep unload protection until the operation is fully resolved. Use request tokens or cancellation so an older load cannot replace a newer selected record. A failed destination load must not silently destroy a retained draft.

### Payments and partial saves

Payment saving currently spans payment and application requests; it is not one transaction across the whole browser operation. Guard every mutation path, including `saveApplicationsForPayment()` and deletion, rather than only the main Save button.

On a partial failure, show the failure, retain the intended values, and reconcile the persisted payment/application state through the existing read endpoints. Do not claim that earlier successful requests were rolled back. If a new payment was created before its applications failed, retain that payment ID so a retry cannot create a second payment.

After reconciliation, keep unresolved differences dirty and make intentional retry possible. Relock only after the complete intended save succeeds. If a write succeeded but the refresh failed, distinguish that condition from a failed write and reconcile before resubmitting.

Use the existing APIs for this work. Consolidating payment saving into a new atomic endpoint is a separate change, not a dependency of this phase.

## 4 Invoice printing while protected

Keep the existing invoice editor and separate Time and Expenses sections. Source-row selections remain browser-local until Save/Print.

- For a new invoice, Save/Print works as it does now without needing Edit Mode.
- For an existing invoice with mode on, Save/Print can update the record, replace its source links, and regenerate the saved HTML using the existing flow.
- For an existing invoice with mode off, offer `Print Saved Invoice`. Open `/api/invoices/{id}/document?autoprint=1`; do not call `/api/invoices/save-print`.
- If there is no saved document, explain that Edit Mode and Save/Print are needed to generate one. Do not generate or overwrite a document through the protected print action.

The document GET already reads the saved HTML file. Preserve that read-only behavior. Handle a missing document or blocked popup visibly. Check edit protection before opening a save popup or sending a write request.

When Save/Print succeeds, clear dirty state and relock the saved invoice even if the browser's printing step is canceled. Canceling the print dialog does not undo the completed save. If a write succeeds and a later editor refresh fails, reconcile the saved result before offering another write.

## 5 Invoice status and overdue days

### Display rules

Keep backend status values and stored terms unchanged. Derive display labels in a shared helper using the saved invoice's issue state, balance, invoice date, and terms.

| Condition | Display label |
| --- | --- |
| Saved invoice has not been issued | Draft |
| Issued invoice is paid under the existing backend rule | Paid |
| Issued invoice has a positive remaining balance and its due date is today or later | Open |
| Issued invoice has a positive remaining balance and is past its due date | Overdue 1 day or Overdue N days |

Use Draft for the unsaved invoice's status display as well; keep its unsaved/new record indication separate from the status tag. Preserve the existing backend treatment of issued zero-value invoices, which remain Open rather than Paid. Drafts and paid invoices never become overdue because of their dates.

Calculate due date from `invoice_date + terms_days`, including Due on receipt and custom stored terms. Determine today from the user's local calendar date, then compare calendar-day numbers using UTC date arithmetic. Do not divide elapsed local timestamps by 24 hours; daylight-saving changes would distort the count. An invoice due today is Open; it becomes Overdue 1 day tomorrow.

Validate dates before calculating. Do not use the localized backend `due_date` string as the calculation source or invent an overdue count for malformed data. Fall back to the stable Draft, Open, or Paid label when the count cannot be calculated.

### Color and consistency

| Days past due | Tag treatment |
| --- | --- |
| 1 through 30 | Amber |
| 31 through 60 | Orange |
| 61 through 90 | Red |
| 91 or more | Dark red |

Use shared classes with readable contrast. Text supplies the exact age so color is not the only signal. Refresh age-dependent tags, filters, and totals when the calendar date changes and when the window regains focus, without resetting the editor or its dirty state.

Apply the same display rules to the invoice browse list and editor, customer statement invoice rows, and invoice rows in Receive Payments. The payment API uses `pending` for issued unpaid invoices and `paid` for paid ones; adapt this known issued-invoice context to the shared display helper rather than treating `pending` as Draft. It already supplies `invoice_date`, `terms_days`, and the true `open_balance_cents`.

Use actual remaining invoice balance for the payment-row tag, not `available_to_apply_cents`, which includes the current payment's allocation. Paid invoices can still appear there when the current payment has an application.

Keep the Overdue filter as one filter covering all positive overdue counts. Preserve the current Open filter's inclusion of issued unpaid invoices, including overdue ones. Use the same helper for the overdue balance metric so tags, filters, and totals agree. Do not change printed invoice documents merely to update a tag's daily age.

## 6 Customer statements and Home

### Customers

Keep one customer browse table as the customer selector. Add Contact and Statement tabs in the selected customer's detail area. Contact contains the current editor; Statement contains the read-only information currently on Home. These two tabs are the proposed layout for this phase, without expanding into a full customer center.

Move these statement details:

- Customer identity and contact information.
- Open A/R, unapplied credit, and net balance.
- Statement generation time.
- Issued invoice detail, including due date, amounts, remaining balance, and the shared status tag.
- Unapplied payment detail and remaining credit.

Use `/api/reports/accounts-receivable?customer_id={id}` for the selected saved customer. This endpoint already supplies the statement and totals. Keep its existing financial definitions, including customers with credit but no open invoices and issued invoices that have been paid.

Fetch statement data independently of the contact form. Switching Contact and Statement tabs does not discard the contact draft, so it does not need a warning. Selecting a different customer does use the discard guard. Use a request sequence or AbortController and check the selected customer ID before displaying a response.

For a new customer draft, show that a statement is available after saving. Do not request the report without a customer ID and accidentally display its default customer's statement. Handle loading, empty statements, and errors within the statement panel. A statement error must not clear the contact draft. After saving a customer, refresh its statement using the saved ID.

Escape customer and database text in generated HTML and use `textContent` for simple values. Keep statements read-only even with Edit Mode on. Viewing them must never create an invoice or payment.

### Home

Remove the customer A/R browse table and selected customer statement from Home. Keep the four financial summary metrics: Open A/R, Unapplied Credit, Net Receivables, and Unbilled Work.

Use concise links to Customers for statements and Invoices for outstanding invoices. Avoid adding another customer directory. Reuse existing overview and reporting responses for the metrics; a new summary endpoint is not required for this phase.

Keep backup and audit export in their current Phase 1 locations. Update Home and Customers help text to match the move.

## 7 Files and implementation sequence

### Expected files

| File or group | Planned work |
| --- | --- |
| `backend/app/pages.py` | Edit capability metadata, revised help text, and script cache versions |
| `frontend/templates/base.html` | Header toggle, protected/active appearance, shared script loading, and badge styles |
| `frontend/js/editor-protection.js` new | Shared mode lifecycle, editor registration, discard confirmation, navigation and unload protection |
| `frontend/js/utils.js` | Shared invoice age/status helpers and guarded same-screen New handling |
| `frontend/js/shell.js` | Header toggle wiring and shared navigation integration without duplicating guard logic |
| `frontend/js/customers.js` and `frontend/templates/customers.html` | Customer protection, detached draft, statement loading, and Contact/Statement tabs |
| `frontend/js/projects.js` and its template | Project and rate protection plus dirty-state integration |
| `frontend/js/time.js` and its template | Existing-entry protection and dirty-state integration; retain form above list |
| `frontend/js/expenses.js` and its template | Existing-entry protection and dirty-state integration; retain form above list |
| `frontend/js/invoices.js` and its template | Detached draft, source-selection protection, saved-document printing, and exact-age tags |
| `frontend/js/payments.js` and its template | Detached draft, application/delete protection, partial-save handling, and consistent invoice tags |
| `frontend/js/app.js` and `frontend/templates/index.html` | Remove duplicate customer browsing and statement rendering; retain summary metrics |
| Documentation | Update workflows, product reference, and relevant repository guidance in the implementation change |

No database migration or API contract change is expected. Confirm this during implementation; update the API Reference if a necessary additive payload change is discovered. Do not change API status vocabulary just to change UI labels.

### Work order

1. Record a baseline of the six screens, existing mutation paths, invoice printing, and report totals. Inventory every action that replaces a draft or writes existing data.
2. Build the shared protection module and header control. Register each screen through a small adapter exposing record identity, current/baseline snapshot, discard behavior, busy state, and a protection rerender callback. Load shared helpers before screen controllers.
3. Integrate one straightforward editor first, then Customers, Projects, Time, and Expenses. Verify rate controls and all existing new/duplicate actions before moving on.
4. Integrate Invoices and Payments. Separate saved objects from drafts, protect source selections and allocations, implement read-only printing, and handle partial saves before considering these screens complete.
5. Add shared exact-age status metadata and wire every invoice display, the Overdue filter, and its metric to it.
6. Move statements to Customers, add guarded customer selection, and remove the duplicate Home content while preserving financial totals.
7. Update `docs/workflows.md`, `docs/tims_ledger_prd.md`, and relevant README/AGENTS guidance for protection, printing, status labels, and statement location. Replace the older Home statement guidance that this phase supersedes.
8. Complete isolated workflow verification, inspect the final diff, and append implementation results and any remaining limitations to this plan.

## 8 Verification

### Data safety and setup

Perform mutation checks against an isolated data directory and a separate server port. Use the checked-in `.venv` and `startup.bat`, with `TIMS_LEDGER_DATA_DIR`, `TIMS_LEDGER_PORT`, `TIMS_LEDGER_FOREGROUND=1`, and `TIMS_LEDGER_SKIP_BROWSER=1` set for that verification process. Check that the configured database and invoice paths resolve into the isolated directory before making writes.

Use isolated fixtures or a consistent SQLite backup copy; do not copy a live database file blindly while it may be writing. Do not reset, reseed, restore over, or use the production database for mutation tests. Keep production invoice HTML unchanged. Restore environment overrides after verification.

### Workflow checks

| Scenario | Expected result |
| --- | --- |
| Open each protected screen | Mode starts off; saved fields and associated mutation controls are protected |
| Enable and disable mode | Correct normal/red appearance, black active text, keyboard operation, and accessible pressed state |
| Attempt an existing-record mutation while locked | Fields/controls block it; submit and mutation helpers send no write request |
| New or supported duplicate on all six screens | Editable with mode off; saving creates a new record and leaves its source unchanged |
| Project rate edits | Built-in/custom controls are protected; allowed edits still obey existing rate rules |
| Existing invoiced Time or Expense | Existing business restrictions remain in force with mode on |
| Successful save | Correct data persisted once; fresh baseline; mode off; editor protected |
| Validation or network failure | Intended draft retained; unsaved warning remains; no false success or automatic relock |
| Partial payment save | Persisted state reconciled; retained created ID; retry does not create a duplicate payment |
| Delete saved payment | Requires mode and confirmation; canceled delete sends no request |
| Navigate, select another record, New, Duplicate, Clear, or same-screen global New while dirty | Confirmation appears; Cancel preserves the complete draft; Continue performs only the intended discard/transition |
| Restore edited values to their originals | Editor becomes clean; no unnecessary warning |
| Refresh, close, back/forward, or cached-page return | Dirty unload protection where supported; returned screen starts with mode off |
| Filter, switch customer detail tabs, refresh statement, or open print window | Draft retained; no spurious discard prompt |
| Locked invoice printing | Saved HTML opens; no save-print POST, invoice/link/timestamp changes, or document rewrite |
| Missing saved invoice document | Clear notice/error; no automatic generation |
| Unlocked invoice Save/Print | Record, Time/Expense links, and HTML updated through the current flow; successful save relocks even if printing is canceled |
| Fast record selection or statement requests | Older responses cannot display under the newer selected record |
| Customer statements | Values match existing report totals; paid invoices, unapplied credit, zero balances, and empty statements render correctly |
| Home after move | Four financial metrics match the baseline; no duplicate customer list or statement |
| Time and Expenses at desktop and narrow widths | Entry form remains above the ledger list |

Use the network log to verify absence of mutation requests while protected. For read-only invoice printing, compare the relevant persisted record/link values and saved file hash before and after, rather than relying only on its visual appearance.

### Date and status checks

Check Draft and Paid precedence, issued zero-value invoices, partial payments, Due on receipt, every standard terms choice, and an existing custom terms value. Test due today, one day overdue, and both sides of the 30/31, 60/61, and 90/91 color boundaries. Include month/year changes, leap day, daylight-saving changes, invalid dates, and a screen left open across midnight. Confirm the payment API's `pending` invoices display as Open or Overdue, never Draft.

Use focused checks for the shared status calculation and state/dirty transitions without installing a test framework unnecessarily. Run JavaScript syntax checks on changed controllers. If Python metadata changes, run the repository's backend `py_compile` check. Run the app through `startup.bat` for manual screen verification, check documentation links, and run `git diff --check` before delivery.

## 9 Completion criteria

- All six saved-record editors require Edit Mode for changes, including invoice sources and payment applications.
- Header state is clear, resets on screen changes, and follows the documented save/failure transitions.
- Unsaved-change cancellation preserves the complete browser draft without a mutation request.
- Protected printing reads the existing invoice document without rewriting data.
- Exact overdue tags agree with filters and metrics and remain correct as the date changes.
- Customers owns statement detail; Home keeps its financial summary without duplicate customer browsing.
- Current invoice layout, separate Time/Expense selection, entry-form placement, and business rules are preserved.
- Documentation and isolated verification results accompany the implementation.

## 10 Deferred work

The original findings also suggested a full-page invoice editor, a merged source-selection list, broader customer-center tabs, payment-allocation redesign, dedicated aging reports, keyboard shortcuts, and an offline stylesheet build. Those are outside this phase. The current invoice layout and separate selection sections are retained by explicit user preference.

Audit history, multiuser authorization, permanent financial-record locking, and an atomic replacement payment API are also outside this UI protection plan. They would require separate requirements and implementation work.

## 11 Implementation results

- Added shared browser-local protection and dirty-baseline handling in `frontend/js/editor-protection.js`, loaded by the base template. The module handles header toggling and navigation directly; no additional shell controller changes were needed.
- Enabled protection on Customers, Projects, Time, Expenses, Invoices, and Payments through page registry metadata. New and duplicate records stay editable; saved records relock after successful saves. Invoice sources, custom rates, payment allocations, and saved payment deletion are covered as well as form fields.
- Detached editable invoice/payment objects from saved browse records and retained ordinary editor drafts across search/filter rerenders. Added guarded transitions, dirty-state restoration, native unload warnings, cached-page mode reset, and loading/request protection.
- Added saved-document printing while protected. Existing Save/Print retains its current document and source-link behavior when editing is enabled.
- Added payment partial-save reconciliation and immediate retention of created IDs. Uncertain invoice/payment creation results disable another save until the user inspects the saved ledger; the draft is retained. Unavailable intended payment allocations must be resolved before retrying.
- Added shared exact-day invoice tags and severity colors across Invoices, Receive Payments, and Customer Statements, including calendar-change refresh.
- Moved statements to Contact/Statement tabs on Customers and removed the duplicate Home directory/statement. Home keeps its four financial summary metrics. Time and Expense forms remain above their lists.
- Updated README, AGENTS guidance, workflows, and the product reference. No API contract, schema, or migration changes were required.

### Verification performed

1. `node --test tests/frontend-phase2.test.cjs`: nine focused regression checks passed. Coverage includes calendar boundaries and invalid data, mode and discard transitions, dirty reversion, navigation cancellation, partial-create baseline preservation, saved-document printing without mutation, detached saved objects, protected save handlers, and payment allocation failure/retry without duplicate creation.
2. JavaScript syntax checks passed for all controllers and shared files. The repository Python `py_compile` check passed.
3. Ran the application through `startup.bat` on port 8014 with a fresh isolated database under `outputs/phase2-verification/`. Confirmed `/api/system/status` resolved to that database before fixture creation or writes.
4. Browser checks covered protected fields on all six screens, active red/black Edit Mode appearance, source-checkbox/allocation/rate protection, exact-day tags at severity boundaries, customer statements, and the preserved Time/Expense form positions. Isolated UI saves on Customers, Projects, Time, Expenses, and Payments persisted the intended values and relocked; a new payment with allocation saved without requiring mode.
5. Exercised the real frontend invoice Save/Print function against the isolated server with a substituted print window. It updated the intended existing invoice, retained its ID, returned the saved document URL, and relocked without initiating a physical print job.
6. Compared the isolated database SQL dump and saved HTML hash before and after the invoice document GET with autoprint. Both remained unchanged.
7. The native discard confirmation appeared in the browser; its cancellation and restoration paths were verified in the focused shared-module checks. Browser-controlled refresh/close warnings retain the browser's wording and interaction requirements.
8. Restarted the existing normal server through `startup.bat` on port 8004 with startup migrations disabled, retaining its production data paths. All eight pages render the current script versions and the expected six Edit Mode controls. Stopped the isolated verification server and closed its temporary browser tab.

Production records and saved invoice documents were not used for mutation checks. Verification fixtures and screenshots are gitignored under `outputs/`; they are not application runtime data or repository fixtures.


## Subsequent business snapshot refinement — October 4, 2026

After Phase 2, Home was simplified to a welcome splash screen. Receive Payments now shows four business totals across all records in the current database: Total Income (recorded payments, including unapplied amounts and negative corrections), Open A/R (issued invoice balances, excluding drafts), Total Expenses, and Non-Billable Expenses (included in Total Expenses). Payment ledger filters do not affect these totals. Totals refresh on screen load and after payment saves/deletes without replacing an editor draft. No automatic annual data reset was added.
