# Invoice Save/Print Implementation Plan

## Goal

Replace the current draft-plus-print invoice workflow with a single Save/Print workflow.

The user should be able to open an invoice, check or uncheck time and expense rows in the browser, and click Save/Print. That action saves the invoice, updates the selected source-record links, regenerates the saved HTML invoice, and opens the HTML so the user can print from the browser.

## Product Rules

1. There are no invoice drafts.
2. Creating a new invoice can begin in browser state, but no database invoice row is needed until Save/Print.
3. Opening an existing invoice loads the invoice editor payload and closes the database connection.
4. Checking and unchecking time or expenses changes only frontend state until Save/Print.
5. Save/Print persists the final selected rows.
6. A checked time entry is saved with `time_entries.invoice_id = invoice.id`.
7. An unchecked previously selected time entry is saved with `time_entries.invoice_id = NULL`.
8. A checked expense is saved with `expenses.invoice_id = invoice.id`.
9. An unchecked previously selected expense is saved with `expenses.invoice_id = NULL`.
10. Existing invoices may be edited and reissued. This intentionally allows accounting history changes without an audit trail.
11. Save/Print always regenerates and overwrites the current saved HTML invoice.
12. GET routes must not issue invoices, change row links, or write HTML files.

## Recommended API

### `GET /api/invoices/bootstrap`

Loads the invoice ledger and project lookup data.

Keep this route read-only.

### `GET /api/invoices/{invoice_id}/editor`

Loads one invoice for editing:

  - invoice header
  - selected time entries
  - selected expenses
  - eligible unbilled time entries for the invoice project
  - eligible unbilled expenses for the invoice project
  - summary totals

Keep this route read-only.

### `POST /api/invoices/save-print`

Creates or updates an invoice, replaces source-row links, regenerates HTML, and returns a printable URL.

Request shape:

```json
{
  "invoice": {
    "id": 201,
    "invoice_number": "INV-2026-014",
    "project_id": 34,
    "invoice_date": "2026-05-20",
    "terms_days": 30,
    "po_number": "PO-123",
    "notes": "Thank you for your business."
  },
  "time_entry_ids": [403, 407],
  "expense_ids": [815]
}
```

For a new invoice, `invoice.id` is omitted or `null`.

Response shape:

```json
{
  "data": {
    "invoice": {},
    "editor": {},
    "printable_url": "/api/invoices/201/document"
  },
  "meta": {
    "screen": "invoice_editor"
  },
  "errors": []
}
```

### `GET /api/invoices/{invoice_id}/document`

Returns the already-saved HTML invoice document.

Rules:

  - read-only
  - no `issued_at` updates
  - no file writes
  - returns `404` if no saved HTML exists
  - may support `?autoprint=1` by injecting print script into the returned document, as long as it does not mutate data

## Backend Transaction

`POST /api/invoices/save-print` should perform one transaction:

1. Validate invoice fields.
2. Validate project exists.
3. Validate at least one selected time entry or expense exists.
4. If invoice ID is missing, insert the invoice.
5. If invoice ID exists, update the invoice.
6. Clear current source links for that invoice:

   ```sql
   UPDATE time_entries SET invoice_id = NULL WHERE invoice_id = ?;
   UPDATE expenses SET invoice_id = NULL WHERE invoice_id = ?;
   ```

7. Validate selected time entries:
   - every ID exists
   - every row belongs to the invoice project
   - every row has `rate_cents > 0`
   - every row is currently unassigned or assigned to this invoice
8. Validate selected expenses:
   - every ID exists
   - every row belongs to the invoice project
   - every row is billable
   - every row is currently unassigned or assigned to this invoice
9. Assign final checked rows:

   ```sql
   UPDATE time_entries SET invoice_id = ? WHERE id IN (...);
   UPDATE expenses SET invoice_id = ? WHERE id IN (...);
   ```

10. Set `issued_at` if it is empty. Keep existing `issued_at` when reissuing unless the product later wants a `reissued_at` field.
11. Generate invoice HTML from the saved invoice and selected rows.
12. Save the HTML file.
13. Update the invoice HTML path and `updated_at`.
14. Commit and close the database connection.

Do not update `payments.amount_cents` from invoice code. Editing invoice history is allowed, but payment amounts should remain actual recorded receipt amounts.

## Database Connection Handling

Use request-scoped SQLite connections. Do not keep a connection open while the user edits in the browser.

Replace the current `connect()` helper with a real closing context manager or make every route close connections explicitly. The preferred shape is:

```python
from contextlib import contextmanager

@contextmanager
def connect(database_path: Path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()
```

If commits remain explicit inside service functions, this context manager should only close. If service functions stop committing, then the context manager should own commit and rollback.

## Data Model Notes

The existing `invoices.pdf_file_name` column now stores an HTML path. That should be renamed when practical.

Recommended migration:

```sql
ALTER TABLE invoices RENAME COLUMN pdf_file_name TO html_file_name;
```

If SQLite compatibility makes column rename awkward, keep the existing column temporarily and update code names first through a compatibility alias.

Recommended saved filename:

```text
invoice-{invoice_id}-{safe_invoice_number}.html
```

This avoids collisions when different invoice numbers sanitize to the same filename.

## Frontend Changes

### State

Keep selected IDs in browser state:

```js
editor: {
  invoice: {},
  selectedTimeEntryIds: new Set(),
  selectedExpenseIds: new Set(),
  eligible_time_entries: [],
  eligible_expenses: []
}
```

Checkbox changes update the sets and recalculate preview totals. They do not call the API.

### Buttons

Remove the separate Print button from the primary workflow.

Use one primary button:

```text
Save/Print Invoice
```

On click:

1. Open a blank popup immediately to avoid popup blockers.
2. Send `POST /api/invoices/save-print`.
3. Receive `printable_url`.
4. Set popup location to `printable_url?autoprint=1`.
5. Reload the invoice ledger/editor state from the response or from `GET /editor`.

### New Invoice

`New Invoice` should create browser-only state. It should not call `POST /api/invoices` until Save/Print.

If the user abandons a new invoice before Save/Print, there is no database cleanup.

### Existing Invoice

When the user clicks an invoice row:

1. load editor payload
2. initialize selected ID sets from selected rows
3. render eligible rows with checked state
4. allow edits in browser state

### Error Handling

Show a clear error if:

  - invoice number is missing or duplicate
  - project is missing
  - no time or expense rows are selected
  - a selected row is now assigned to another invoice
  - a selected row is no longer eligible
  - HTML file write fails

## HTML Rendering

Continue escaping user data in generated invoice HTML.

Recommended improvement:

  - move the invoice HTML into a template file
  - use autoescaping
  - keep date and currency formatting helpers in Python

This is not required for the first Save/Print cleanup, but it will make invoice layout maintenance much easier.

## Security Fix Required

Fix invoice UI stored XSS before or during this workflow change.

Any user-controlled value inserted into the DOM must be escaped or assigned through `textContent`, including:

  - invoice number
  - customer name
  - project number
  - PO number
  - notes
  - time descriptions
  - rate codes
  - expense vendor
  - expense category
  - expense description

## Test Plan

### Backend Tests

1. New invoice Save/Print creates invoice, assigns selected time and expense rows, writes HTML, and returns printable URL.
2. Existing invoice Save/Print updates header fields, replaces selected rows, clears unchecked prior rows, writes updated HTML, and returns printable URL.
3. Unchecked rows become eligible for a different invoice.
4. Save/Print rejects rows assigned to another invoice.
5. Save/Print rejects empty row selection.
6. GET document returns saved HTML without changing `issued_at`, row links, `updated_at`, or file contents.
7. Paid invoice edit does not alter `payments.amount_cents`.
8. Database connections close cleanly on Windows and startup tests can remove temp DB files.

### Browser E2E Tests

1. Open existing invoice, uncheck one selected row, check one eligible row, click Save/Print, verify popup HTML contains the final rows.
2. Verify unchecked row no longer has that invoice number in the time or expense module.
3. Create a new invoice in browser state, select rows, click Save/Print, verify invoice appears in ledger and saved HTML exists.
4. Verify checkbox clicks alone do not persist after reload unless Save/Print was clicked.
5. Verify malicious text is displayed as text, not executed as HTML.

## Implementation Sequence

1. Fix SQLite connection lifecycle.
2. Add `InvoiceSavePrintWrite` payload model.
3. Add backend save/print service function with one transaction.
4. Add `POST /api/invoices/save-print`.
5. Add read-only `GET /api/invoices/{id}/document`.
6. Update frontend checkbox behavior to be local-only.
7. Replace Save and Print buttons with one Save/Print button.
8. Remove or retire immediate `/selection` calls from the invoice UI.
9. Fix invoice UI escaping.
10. Update backend and e2e tests.
11. Update docs and remove stale draft language from invoice UI copy.

## Open Questions

1. Should `issued_at` remain the original first-issued timestamp, or should reissues also track `reissued_at`?
2. Should existing paid invoice edits automatically leave invoices underpaid/overpaid based on existing payment applications, or should payment applications be cleared when invoice totals change?
3. Should `invoice_number` be user-entered for new invoices, auto-generated on Save/Print, or both?
