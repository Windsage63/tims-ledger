# Winds Ledger - Agent Instructions

## Project Overview

Winds Ledger is a local, desktop-first accounting workflow for project billing. It uses a FastAPI backend, vanilla HTML/JavaScript frontend, SQLite persistence, and generated HTML invoice documents.

The current product reference docs are:

- [docs/winds_ledger_prd.md](docs/winds_ledger_prd.md)
- [docs/workflows.md](docs/workflows.md)
- [docs/API Reference.md](docs/API%20Reference.md)

## Environment And Commands

Never install packages into the global Python environment. Use the checked-in `.venv` only.

Start each terminal session by checking/activating the venv:

```powershell
if ($env:VIRTUAL_ENV) { $env:VIRTUAL_ENV } else { . .\.venv\Scripts\Activate.ps1 }
```

Run the app through the repo startup script, not an ad hoc uvicorn command:

```powershell
.\startup.bat
```

Use the lightweight backend syntax check when changing Python:

```powershell
. .\.venv\Scripts\Activate.ps1
python -m py_compile (Get-ChildItem backend\app -Filter *.py | ForEach-Object { $_.FullName })
```

There is no formal automated test suite yet. For frontend or workflow changes, run the app with `.\startup.bat` and verify the affected screen manually.

## Architecture

```text
backend/app/
  main.py          FastAPI app factory and routes
  db.py            SQLite connection and migration helpers
  config.py        Data, database, and migration paths
  customers.py     Customer models and CRUD helpers
  projects.py      Projects, built-in rates, custom rates
  time_entries.py  Time source records and invoice eligibility
  expenses.py      Expense source records and categories
  invoices.py      Invoice editor payloads, Save/Print, HTML documents
  payments.py      Payments and invoice applications
  reporting.py     AR reports and XLSX audit export
  backups.py       ZIP backup/list/restore behavior

frontend/html/     One page per screen
frontend/js/       One stateful vanilla JS controller per screen
migrations/        Ordered SQL migrations applied at startup
app-data/          Local runtime data; gitignored
```

## Data Safety

`app-data/winds-ledger.db` is the source-of-truth SQLite database. `app-data/invoices/` stores generated invoice HTML documents. Treat both as local production data.

Do not wipe, reset, reseed, or replace the database unless the user explicitly asks. Prefer read-only inspection for debugging. If restore behavior is needed, use the application backup/restore path so a safety backup is created first.

Normal backups live in `app-data/backups/` as `Winds-Ledger-Backup-{date-timestamp}.zip`. Restore safety backups live in `app-data/backups/safety/` and should not be listed as normal restore candidates. The XLSX export is for audit/readability, not backup.

## Backend Conventions

- Routes in `main.py` use `response_envelope(data, screen=...)` for JSON responses.
- Domain modules expose Pydantic write models plus functions that accept a `sqlite3.Connection`.
- Use `with connect(settings.database_path) as connection:` so `row_factory` and foreign keys are applied.
- Commit inside create/update helpers that directly mutate user records. Multi-step invoice/payment flows use `*_without_commit` helpers and commit once after all links/documents are updated.
- Keep migrations additive and ordered under `migrations/`; startup applies pending migrations unless disabled by settings.

## Frontend Conventions

- Each screen owns its state in `frontend/js/{screen}.js` and talks directly to its matching API endpoints.
- Escape user/database text before inserting template HTML. Existing screen files define `escapeHtml`; use it for table rows, cards, and option labels.
- Prefer `textContent` helpers for simple text updates and event delegation for generated rows/lists.
- Preserve the dense desktop ledger layout: sidebar navigation, metrics, browse tables, and editor panels.

## Product Rules To Preserve

- Time billability comes from the selected rate. Rate `0` is non-billable; there is no separate time billable toggle.
- Fixed-fee and materials-order style billing is represented through custom project rates and unit entries in time, not manual invoice lines.
- Expense categories are exactly: `Materials`, `Lodging`, `Airfare`, `Mileage`, `Perdiem`, `Rental Car`, `Gas`, `Parking`, `Tolls`, `Meals`, `Entertainment`, `Gifts`, `Freight`, `Misc.`.
- Invoice source-row checkbox changes stay browser-local until Save/Print. Save/Print creates or updates the invoice, replaces time/expense invoice links, writes the saved invoice HTML, and opens it for printing.
- Printed invoice project references should read `{project number} - {project description}`.
- PO number is not part of the active invoice UI.
- Overview should prioritize metrics, accounts receivable, customer statement detail, XLSX audit export, and backup/restore controls.

## Documentation

When code changes API routes, workflow behavior, invoice output, backup/restore behavior, or core business rules, update the matching docs in `docs/` in the same change.
