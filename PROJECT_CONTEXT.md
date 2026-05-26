# Windsage Ledger Project Context

## Product

**Name:** Windsage Ledger

**Tagline:** Simple books I can understand.

Windsage Ledger is a local-first accounting operations app for Air Advantage. It is intended to replace fragile spreadsheet accounting workflows with a structured app for customers, projects, time entries, expenses, invoices, payments, customer advances, customer balances, reports, and future receipt OCR.

## Why This Exists

The current spreadsheet is useful but has become too complex for reliable accounting. The original invoice sheet can produce invoices, but the workbook does not maintain a clean invoice register, payment ledger, or reliable customer balance system. Prior attempts to rebuild the workbook showed that spreadsheet formula logic is too fragile for the desired workflow.

The app should keep the useful mental model of the workbook while moving accounting truth into explicit records and transaction-safe backend services.

## Core Architecture Direction

  - Backend: Python + FastAPI
  - Frontend: React + TypeScript + Vite
  - Database: SQLite for the local-first MVP
  - ORM: SQLAlchemy or SQLModel
  - Migrations: Alembic
  - Reports: PDF invoices plus Excel/CSV exports
  - Future automation: Python receipt OCR pipeline

## Key Decisions

1. Build a local-first app first, not a cloud SaaS product.
2. Use Python for backend accounting logic, imports, exports, PDF generation, and OCR.
3. Use React for the modern interactive UI.
4. Store invoices, payments, and payment applications separately.
5. Generate invoices from approved time and expense records, not from manually typed invoice lines.
6. Treat OCR output as suggestions that require review before creating approved accounting records.
7. Preserve source workbook and Stitch design files as references, not as implementation targets.

## First Proof Workflow

The first working milestone should prove this flow:

```text
Customer + Project + Time + Expense
-> Invoice Builder
-> Invoice 662 style PDF
-> Payment Application
-> Customer Balance
```

If this flow reproduces the existing invoice behavior and fixes customer balance tracking, the architecture is validated.

## Important Reference Files

  - `README.md`
  - `docs/architecture/architect-plan-accounting-app-v1.md`
  - `docs/discovery/Accounting Workbook Improvement Plan.md`
  - `docs/discovery/Accounting Workbook Refined Requirements.md`
  - `docs/product/design-principles.md`
  - `docs/product/workflows.md`
  - `docs/adr/`
  - `references/workbooks/Timesheet Log and Project Tracking 2025.xlsx`
  - `references/stitch/`

## Current Repo State

The repo has initial project scaffolding plus the first backend accounting foundation:

- `backend/` contains FastAPI routes for customers, projects, expense categories, time entries, and expenses.
- `backend/` contains SQLAlchemy models, Alembic migration setup, accounting services, and backend tests for invoice/payment/source-record rules.
- `frontend/` contains a minimal React/Vite placeholder app.
- `docs/` contains architecture, discovery, product, and ADR notes.
- `references/` contains the workbook and Stitch concept files.

Python dependencies are installed into `.venv`; frontend dependencies are installed with npm.
Backend and frontend checks have been run successfully.

## Suggested Next Steps

1. Build invoice candidate selection endpoints from unbilled time and expenses.
2. Add draft invoice creation and send/finalize API routes.
3. Add payment and payment application API routes.
4. Add customer balance calculation endpoint.
5. Replace the placeholder frontend with the first real app shell and navigation.
6. Build the proof workflow around invoice `662`.

## Working Style

Prefer small, verifiable increments. Avoid broad generated code that obscures accounting rules. Every accounting workflow should have backend tests before relying on the UI.
