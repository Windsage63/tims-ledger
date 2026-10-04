# Tim's Ledger

![Tim's Ledger hero](docs/assets/tims-ledger-hero.png)

Tim's Ledger is a local, desktop-first accounting workflow for project billing. It uses a FastAPI backend, server-rendered Jinja2 HTML with vanilla JavaScript controllers, SQLite persistence, and generated HTML invoice documents.

The app is meant to replace a spreadsheet-driven workflow, not become a full accounting platform. It focuses on customers, projects, time, expenses, invoices, payments, accounts receivable, audit export, and backup/restore.

## Documentation

  - [Product requirements](docs/tims_ledger_prd.md)
  - [Core workflows](docs/workflows.md)
  - [API reference](docs/API%20Reference.md)

## Tech Stack

  - Backend: FastAPI and SQLite
  - Frontend: Jinja2 pages sharing one layout, with vanilla JavaScript controllers
  - Runtime data: `app-data/`
  - Migrations: ordered SQL files in `migrations/`

## Project Layout

```text
backend/app/       FastAPI routes, domain modules, SQLite helpers, reporting, backups
frontend/templates/ Shared base layout and one Jinja2 content template per screen
frontend/js/       One vanilla JavaScript controller per screen plus shared utilities
migrations/        Startup-applied SQLite migrations
docs/              Product, workflow, and API documentation
app-data/          Local runtime data, database, invoices, and backups; gitignored
```

## First-Time Install

After downloading and unzipping the repository, run the installer from the repo root:

```powershell
.\install.bat
```

`install.bat` checks for Python 3.10 or newer, tries to install Python 3.13 with `winget` if Python is missing, creates `.venv`, and installs `backend/requirements.txt` into that virtual environment. It does not install packages globally.

## Running Locally

Use the project virtual environment. Do not install packages globally. If `.venv` is missing, run `.\install.bat` first.

```powershell
if ($env:VIRTUAL_ENV) { $env:VIRTUAL_ENV } else { . .\.venv\Scripts\Activate.ps1 }
```

Start the application with the repo startup script:

```powershell
.\startup.bat
```

By default, the app runs at:

```text
http://127.0.0.1:8004/
```

`startup.bat` starts `uvicorn`, waits for `/api/health`, and opens the browser unless `TIMS_LEDGER_SKIP_BROWSER=1` is set.

Pages require the running application; opening template files directly in a browser is not supported. Existing page URLs such as `/frontend/html/customers.html` render through FastAPI. JavaScript remains available under `/frontend/js/`; template source is not publicly served.

## Shared Frontend Layout

`frontend/templates/base.html` owns the document setup, theme, sidebar, main wrapper, and shared script loading. Each screen extends it with its main content and page actions. `utils.js` supplies toasts, segmented filter state, calendar due-date helpers, and the post-bootstrap `#new` hook; `shell.js` owns menus and shared backup state/events. `editor-protection.js` owns Edit Mode, normalized draft baselines, discard confirmation, and navigation/unload protection. Update the shared theme or layout here once for all screens. The application maintains a minimum layout width of 1024px and keeps the sidebar beside the content at every window width; narrower windows use horizontal scrolling.

`backend/app/pages.py` contains the ordered page registry: page filenames, titles, navigation labels, controller URLs, navigation groups, headings, help text, new-record labels, and Edit Mode capability. Update this registry to change menu entries. Navigation groups are Home, Sales (Invoices, Receive Payments, Customers), and Work (Projects, Time, Expenses), with Settings at the bottom. Navigation highlighting and `aria-current` are rendered on the server.

## Configuration

The backend reads these environment variables:

  - `TIMS_LEDGER_DATA_DIR`: Runtime data directory. Defaults to `app-data/`.
  - `TIMS_LEDGER_DB_PATH`: SQLite database path. Defaults to `app-data/tims-ledger.db`.
  - `TIMS_LEDGER_MIGRATIONS_DIR`: Migration directory. Defaults to `migrations/`.
  - `TIMS_LEDGER_SKIP_STARTUP_MIGRATIONS`: Set to `1` to skip applying pending migrations at startup.

The startup script also reads:

  - `TIMS_LEDGER_HOST`: Defaults to `127.0.0.1`.
  - `TIMS_LEDGER_PORT`: Defaults to `8004`.
  - `TIMS_LEDGER_WINDOW_TITLE`: Backend terminal title.
  - `TIMS_LEDGER_FOREGROUND`: Set to `1` to run uvicorn in the current terminal.
  - `TIMS_LEDGER_SKIP_BROWSER`: Set to `1` to avoid opening the browser.

## Data Safety

`app-data/tims-ledger.db` is the source-of-truth database. `app-data/invoices/` stores generated invoice HTML documents. Both are local production data and are gitignored.

Use the application backup and restore workflow instead of manually replacing the database. Normal backups are written to `app-data/backups/` as `Tims-Ledger-Backup-{date-timestamp}.zip`. Restore safety backups are written under `app-data/backups/safety/` and are not listed as normal restore choices.

Settings contains the Company profile, Backup & Restore, and XLSX audit export. Every page header provides Back up and a last-backup indicator. Home is a welcome splash screen with an original ledger illustration in `frontend/assets/splash-ledger.png`; its generation prompt is saved beside the image. Static artwork is served only from `/frontend/assets/`. Receive Payments shows four unfiltered business totals: Total Income, Open A/R, Total Expenses, and Non-Billable Expenses. Total Income sums recorded payments (including unapplied amounts and negative corrections); Open A/R sums issued invoice balances; Non-Billable Expenses is included in Total Expenses. Totals cover every record in the current database and refresh after payment saves/deletes. Customers provides Contact and Statement tabs for the selected customer, including invoice detail and unapplied payments. The XLSX export is for audit and readability. It is not the backup format.

The + New menu opens a browser-local draft after the destination screen finishes loading. Invoice terms are selectable as Due on receipt or Net 10 / 15 / 30 / 45 / 60. The ledger shows due date and balance with Draft, Open, Paid, and exact-day overdue labels such as `Overdue 1 day` or `Overdue 47 days`. Overdue tag colors progress at 31, 61, and 91 days past terms. Overdue means a printed invoice has a positive balance and a due date before the local calendar date; Open includes all printed unpaid invoices, including overdue ones.

Customers, Projects, Time, Expenses, Invoices, and Payments start with saved records protected. Enable the header's EDIT MODE button to change them; red with black letters indicates editing is enabled. Mode resets on screen changes and after successful saves/deletes. New records and duplicates remain editable without it. Discarding a modified draft asks for confirmation, including record selection and navigation; browser refresh/close uses the browser's native unsaved-change warning.

While an invoice is protected, Print Saved Invoice reads its existing HTML document without saving or regenerating it. Enable Edit Mode to use Save/Print for an existing invoice. Settings is outside this record protection workflow.

## Verification

Focused frontend regression checks are available with `node --test tests/frontend-phase2.test.cjs`; they need no extra packages. Manual workflow verification remains required. For Python changes, run the lightweight syntax check:

```powershell
. .\.venv\Scripts\Activate.ps1
python -m py_compile (Get-ChildItem backend\app -Filter *.py | ForEach-Object { $_.FullName })
```

For frontend and workflow changes, start the app with `.\startup.bat` and verify the affected screen manually. Use an isolated data directory and separate port for mutation checks; confirm `/api/system/status` points to the intended test database before writing.

## Current Product Rules

  - Time billability comes from the selected project rate. A rate of `0` is non-billable.
  - Fixed-fee and materials-order billing are represented through custom project rates and unit entries in time.
  - Expense categories are limited to `Materials`, `Lodging`, `Airfare`, `Mileage`, `Perdiem`, `Rental Car`, `Gas`, `Parking`, `Tolls`, `Meals`, `Entertainment`, `Gifts`, `Freight`, and `Misc.`.
  - Invoice source-row checkbox changes remain browser-local until Save/Print.
  - Printed invoice project references read `{project number} - {project description}`.
  - PO number is not part of the active invoice UI.
  - Payment drafts stay browser-local until Save Payment. Payment references are optional, zero-dollar drafts are allowed, and negative payments support credits or corrections.
