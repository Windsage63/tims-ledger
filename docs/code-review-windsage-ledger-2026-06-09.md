# Windsage Ledger Code Review

## Summary

Windsage Ledger has a clear FastAPI plus SQLite structure and the invoicing feature has real API, browser, and file-output coverage. The invoicing system should now be aligned to a simpler product decision: invoices are edited in browser state, checkbox changes are persisted only when the user clicks Save/Print, and that one action updates the database, regenerates the saved HTML invoice, and opens it for browser printing.

Finding count: **Blocker: 1**, **Major: 7**, **Minor: 3**, **Nit: 0**.

## Product Decision For Invoices

The desired invoice workflow is not a draft workflow. The database should not create or update invoice records just because the user clicks checkboxes. The browser editor may hold unsaved invoice state, but persistence should happen only through the Save/Print action.

Target behavior:

1. Opening an existing invoice loads invoice fields, selected time/expense rows, eligible rows, and totals, then closes the database connection.
2. Creating a new invoice starts a temporary browser-side editor. No invoice row is required until Save/Print.
3. Checking or unchecking time and expenses updates only frontend state and preview totals.
4. Save/Print creates or updates the invoice, replaces all time/expense invoice links, saves the HTML invoice document, and opens it for browser printing.
5. If a selected time entry or expense is saved, its `invoice_id` is set to the invoice ID. If an existing selected row is unchecked and saved, its `invoice_id` is cleared so it can be used on a different invoice.
6. Changing accounting history is explicitly acceptable for this application. The system does not need an immutable audit trail for invoice edits.

## Critical Issues (Security, Correctness, Performance)

- **Blocker** Stored XSS is possible in the invoice UI because user-controlled ledger data is inserted with `innerHTML`.
  - Evidence: `backend/app/static/invoices.js:332-345` injects invoice number, customer, project, date, and status markup directly into table rows. `backend/app/static/invoices.js:425-447` injects time-entry descriptions, rate codes, vendors, categories, and expense descriptions directly into checkbox labels.
  - Impact: customer names, invoice numbers, project numbers, time descriptions, vendors, or expense descriptions can contain HTML or event handlers. When rendered, that script runs in the app origin and can call the local API to mutate invoices, payments, and customer data.
  - Suggested improvement: render dynamic values via DOM text nodes, or add a single `escapeHtml()` helper and apply it to every interpolated data value before building template strings. Keep trusted markup, CSS classes, and data attributes separate from user data.

- **Major** SQLite connections are leaked throughout the app because `with connect(...) as connection:` does not close `sqlite3.Connection`.
  - Evidence: `backend/app/db.py:28-32` returns a raw SQLite connection. Python's SQLite context manager commits or rolls back but does not close the connection. Routes use this pattern heavily, for example `backend/app/main.py:292-300`, `backend/app/main.py:310-311`, and `backend/app/main.py:348-349`.
  - Runtime evidence: direct backend unittest discovery produced many `ResourceWarning: unclosed database` warnings and `test_app_startup` failed on Windows with `PermissionError: [WinError 32]` because `winds-ledger-startup.db` remained locked.
  - Suggested improvement: provide a real context manager:
    ```python
    from contextlib import contextmanager

    @contextmanager
    def connect(database_path: Path):
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()
    ```
    Then remove redundant scattered commits or keep the current explicit commits and make the context manager only close.

- **Major** `GET /api/invoices/{invoice_id}/print` mutates invoice state and writes files instead of Save/Print being the single persistence action.
  - Evidence: the route is declared as a GET in `backend/app/main.py:307-331`, but calls `save_invoice_print_document()` at `backend/app/main.py:310-311`. That function calls `mark_invoice_printed()` at `backend/app/invoices.py:1011`, writes the HTML file at `backend/app/invoices.py:1031`, and updates `pdf_file_name` at `backend/app/invoices.py:1032-1036`.
  - Impact: a refresh, browser prefetch, crawler, or accidental link open can issue an invoice and rewrite its stored HTML. This also preserves a separate print action that the desired workflow no longer needs.
  - Suggested improvement: replace the mutating GET with a single `POST /api/invoices/save-print` endpoint that creates or updates the invoice, replaces source-row links, writes the HTML document, and returns a printable URL. Keep GET routes read-only for viewing already-saved HTML.

- **Major** Editing a paid invoice can rewrite payment amounts, which mutates cash records rather than only changing invoice row selection.
  - Evidence: `reconcile_invoice_payment_applications()` expands payment applications and, if no remaining payment capacity exists, updates `payments.amount_cents` at `backend/app/invoices.py:824-835`. It is called from invoice header updates at `backend/app/invoices.py:878-882` and selection updates at `backend/app/invoices.py:968-972` when the invoice was previously paid.
  - Impact: changing invoice history is acceptable for this app, but changing a payment amount as a side effect of invoice editing is a different operation. It can make recorded receipts stop matching actual received cash.
  - Suggested improvement: when Save/Print changes invoice selections or totals, update invoice links and regenerate balances from the existing payment applications. Do not alter `payments.amount_cents` from invoice code. If the invoice becomes underpaid or overpaid, let the payment/application screens reflect that.

## Logic & Edge Cases

- **Major** The current `Save Invoice` action does not persist checkbox selections and saved HTML in one transaction.
  - Evidence: `saveDraftInvoice()` only POSTs or PUTs invoice JSON in `backend/app/static/invoices.js:560-581`. The only backend path that writes HTML is the print route through `save_invoice_print_document()` in `backend/app/main.py:307-311` and `backend/app/invoices.py:1006-1037`.
  - Impact: after editing an invoice and clicking `Save Invoice`, `pdf_file_name` can still point at stale HTML. Checkbox changes are also currently persisted immediately through `/selection`, which conflicts with the desired browser-edit-then-save model.
  - Suggested improvement: replace both `saveDraftInvoice()` and `printInvoice()` with one `savePrintInvoice()` flow. The request should include invoice fields plus final `time_entry_ids` and `expense_ids`; the backend should create/update, replace links, write HTML, commit, close, and return a printable URL.

- **Major** Invoice editability is carrying draft-era assumptions that are no longer needed.
  - Evidence: the editable invoice payload contains only number, project, date, terms, PO, and notes in `backend/app/invoices.py:17-23`. The UI form omits `terms_days`; it preserves the current value at `backend/app/static/invoices.js:480` instead of allowing edits. Line items are checkboxes only at `backend/app/static/invoices.js:419-449`, and source rows on printed invoices are read-only through the time and expense APIs at `backend/app/time_entries.py:195-207` and `backend/app/expenses.py:198-210`.
  - Impact: the invoice editor mixes three concepts: draft invoice creation, issued invoice editing, and immediate source-row persistence. That makes the Save/Print behavior harder to reason about.
  - Suggested improvement: remove draft persistence and immediate checkbox persistence from the invoice editor. Keep line editing to source-row inclusion/exclusion unless a separate future requirement asks for overriding descriptions, rates, or quantities. Add a visible `terms_days` field if terms should remain invoice metadata.

- **Major** Changing an invoice's project clears selected rows immediately on save and needs to align with the new Save/Print transaction.
  - Evidence: `update_invoice()` calls `clear_invoice_selection()` whenever `payload.project_id != existing["project_id"]` at `backend/app/invoices.py:849-850`.
  - Impact: in the target workflow, clearing old row links is acceptable when the user saves a new project selection, but it should happen as part of the same Save/Print transaction that assigns the final checked rows and regenerates HTML. Partial header saves should not silently clear row links.
  - Suggested improvement: move project-change cleanup into the new atomic Save/Print endpoint. Clear links for the old invoice, validate the final selected rows against the new project, assign checked rows, write HTML, and commit together.

- **Minor** Sanitized HTML filenames can collide.
  - Evidence: `stored_invoice_file_name()` normalizes many different invoice numbers to the same basename at `backend/app/invoices.py:994-997`, and `save_invoice_print_document()` writes that path at `backend/app/invoices.py:1020-1031`.
  - Impact: unique invoice numbers such as `INV/001` and `INV:001` both become `INV-001.html`, so one invoice's saved HTML can overwrite the other's.
  - Suggested improvement: include the invoice database ID in the filename, for example `invoice-{id}-{safe_number}.html`.

## Simplification & Minimalism

- **Minor** Invoice HTML rendering is a large hand-built format string that mixes presentation, formatting logic, and business fields.
  - Evidence: `build_invoice_print_html()` spans the generated document and CSS in `backend/app/invoices.py:166-520`, while `render_invoice_table_rows()` builds row markup separately at `backend/app/invoices.py:87-163`.
  - Impact: the current output works, and escaping is handled better than the frontend UI, but future invoice layout edits will be brittle and hard to test in small pieces.
  - Suggested improvement: move invoice HTML into a template file, preferably with Jinja2 autoescaping. Keep money/date formatting helpers in Python and snapshot-test the rendered HTML.

## Elegance & Idiomatic Enhancements

- **Minor** Pydantic list defaults should use `default_factory`.
  - Evidence: `InvoiceSelectionWrite` uses `time_entry_ids: list[int] = []` and `expense_ids: list[int] = []` at `backend/app/invoices.py:55-57`.
  - Impact: Pydantic usually protects against shared mutable defaults, but this is still a fragile pattern and easy to copy into plain Python models where it becomes a real bug.
  - Suggested improvement:
    ```python
    from pydantic import Field

    class InvoiceSelectionWrite(BaseModel):
        time_entry_ids: list[int] = Field(default_factory=list)
        expense_ids: list[int] = Field(default_factory=list)
    ```

## Documentation & Testability

- **Major** The configured backend test script fails from the repository root.
  - Evidence: `package.json:6` runs unittest discovery against `backend/tests` from the repo root. The test modules import `app` and `tests`, which are only importable when `backend` is on `PYTHONPATH` or the command runs from `backend`.
  - Runtime evidence: `npm run test:backend` failed with `ModuleNotFoundError: No module named 'app'` and `ModuleNotFoundError: No module named 'tests'`.
  - Suggested improvement: set `PYTHONPATH=backend` in the script, or run the command with `cwd=backend`, for example:
    ```json
    "test:backend": "cd backend && ..\\.venv\\Scripts\\python.exe -m unittest discover -v -s tests -p test_*.py"
    ```

- **Major** The invoice tests cover print-after-save but not the desired single Save/Print transaction.
  - Evidence: `backend/tests/test_invoices_api.py` validates stored HTML after calling `/print`, and `e2e/invoices.spec.js` also clicks `#print-invoice-button` before checking the file. There is no test proving that `Save Invoice` itself updates the stored `.html` document.
  - Impact: the current tests pass while the product's desired action remains untested. They also normalize immediate checkbox persistence instead of browser-local selection until Save/Print.
  - Suggested improvement: add API and browser tests for creating a new invoice from checked source rows, editing an existing invoice, unchecking rows, clicking Save/Print, verifying `invoice_id` links are assigned/cleared only after save, and verifying the saved HTML is regenerated.

## Positive Observations

- The invoice HTML generator escapes printed invoice fields with `html.escape`, which avoids the same XSS problem in the saved print document.
- The invoice editor payload separates selected rows from eligible rows, which makes the editable source selection model easy to reason about.
- The new e2e test directly exercises the current invoice workflow and can be adapted into the desired Save/Print workflow.
- The payment and invoice APIs share clear response envelopes, making browser code and tests consistent.
- The ledger has enough shape to survive first contact with a user, which is more than most accounting code deserves.

## Prioritized Findings Summary

| # | Severity | Section | Finding | Effort |
|---|---|---|---|---|
| 1 | **Blocker** | Critical Issues | Stored XSS through invoice UI `innerHTML` rendering | Med |
| 2 | **Major** | Critical Issues | SQLite connections are leaked and lock files on Windows | Med |
| 3 | **Major** | Critical Issues | GET print endpoint mutates state instead of Save/Print owning persistence | Med |
| 4 | **Major** | Critical Issues | Paid invoice edits can rewrite payment amounts | Med |
| 5 | **Major** | Logic & Edge Cases | Save Invoice does not persist selections and HTML atomically | Med |
| 6 | **Major** | Logic & Edge Cases | Invoice editor still carries draft/immediate-save assumptions | Med |
| 7 | **Major** | Logic & Edge Cases | Project change cleanup must move into Save/Print transaction | Med |
| 8 | **Major** | Documentation & Testability | Backend test script fails from repo root | Low |
| 9 | **Major** | Documentation & Testability | Missing Save/Print transaction tests | Low |
| 10 | **Minor** | Logic & Edge Cases | Sanitized invoice HTML filenames can collide | Low |
| 11 | **Minor** | Simplification | Large hand-built invoice HTML string is brittle | Med |
| 12 | **Minor** | Elegance | Selection model uses mutable list defaults | Low |

## Verification

- `npm run test:backend`: failed before tests imported because `backend` is not on `PYTHONPATH`.
- `..\.venv\Scripts\python.exe -m unittest discover -v -s tests -p test_*.py` from `backend`: 30 tests passed, 1 failed due to a locked SQLite temp DB, with repeated unclosed database warnings.
- `npm run test:e2e`: passed, 1 browser invoice test.
