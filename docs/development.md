# Development Setup

## Runtime Choices

  - Backend uses Python in the repo-root `.venv`.
  - Frontend uses Node.js and npm.
  - The frontend package manager is npm. Commit `frontend/package-lock.json` when dependencies change.

## Windows Quick Start

From the repository root:

```powershell
.\startup.bat
```

`startup.bat` launches the backend and frontend in separate windows, waits briefly for the dev servers to come up, and opens `http://127.0.0.1:5173` in your default browser.

The script expects:

  - `./.venv/Scripts/python.exe` to exist
  - `npm` to be available on `PATH`

Use the manual commands below when you want to run only one service or debug startup issues directly.

## Backend

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .\backend[dev]
```

Run backend checks:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m ruff check .
..\.venv\Scripts\python.exe -m alembic upgrade head
```

Seed development data:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.dev.seed
```

Start the API:

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8004
```

## Frontend

Install dependencies:

```powershell
cd frontend
npm install
```

Run frontend checks:

```powershell
npm run lint
npm run build
npm run test
```

`npm run test` currently succeeds with no test files present. Frontend behavior is not yet covered by checked-in Vitest tests.

Start the Vite dev server:

```powershell
npm run dev
```

If the backend is running on a non-default port, create `frontend/.env.local`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8001
```

## Full Local Workflow

On Windows, you can use `startup.bat` from the repository root.

For manual startup, run the backend and frontend in separate terminals:

```text
Backend:  http://127.0.0.1:8004
Frontend: http://127.0.0.1:5173
```

After starting the backend, API docs are available at:

```text
http://127.0.0.1:8004/docs
```

The first implemented API groups are:

```text
/api/customers
/api/projects
/api/expense-categories
/api/time-entries
/api/expenses
/api/invoice-builder/candidates
/api/invoices
/api/payments
/api/customers/{customer_id}/balance
/api/reports/ar-aging
/api/reports/ar-aging.csv
/api/reports/open-invoices.csv
/api/imports/workbook/preview
/api/receipts
/api/ocr-jobs/{job_id}
/api/backups
```

The current React app wires these workflow areas directly:

```text
Dashboard
Customers
Projects
Time
Expenses
```

The remaining navigation areas are still placeholder screens while the backend workflows are wired into the UI.
