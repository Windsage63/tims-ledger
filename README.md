# Windsage Ledger

**Simple books I can understand.**

Windsage Ledger is a local-first accounting operations app for project-driven consulting work. The goal is to replace fragile spreadsheet accounting logic with a structured, understandable system for customers, projects, time, expenses, invoices, payments, credits, and reports.

## Current Status

This repository now has a working FastAPI backend with tested accounting workflows for customers, projects, time entries, expenses, invoices, payments, customer balances, report exports, workbook preview, receipt OCR review, and backup creation.

The React app has moved beyond the placeholder stage. It includes the app shell, dashboard, and first create/list screens for customers, projects, time entries, expenses, and expense categories. Invoice, payment, report, import, and backup screens are still frontend placeholders backed by existing or partial backend APIs.

## Current Stack

  - Backend: Python, FastAPI, SQLite, SQLAlchemy 2.x, Alembic
  - Frontend: React, TypeScript, Vite, npm
  - Reports: PDF invoices and Excel/CSV exports
  - Automation: future receipt OCR pipeline through the Python backend

## Project Goals

  - Build invoices from approved time and expenses instead of manually retyping line items.
  - Track customer balances through invoices, payments, payment applications, and credits.
  - Support customer advances and partial payments clearly.
  - Keep receipts and expense records ready for future OCR-assisted entry.
  - Preserve simple local ownership of the data with easy backup and export.

## Repository Layout

```text
backend/             FastAPI application source
frontend/            React application source
docs/architecture/   Architecture blueprints and technical decisions
docs/discovery/      Workbook analysis and refined requirements
docs/development.md  Local development setup and check commands
docs/product/        Product workflow, UX, and screen planning
references/          Source workbook and Stitch design references
```

## Development

See `docs/development.md` for local setup, check commands, and dev server startup.

See `docs/roadmap.md` for the current implementation roadmap.

## First Proof Workflow

The proof workflow is partially implemented today. The backend covers:

```text
Customer + Project + Time + Expense
-> Invoice candidate selection and draft creation
-> Invoice send/finalize
-> Payment application
-> Customer balance and AR aging
```

The remaining gap is the React workflow for invoices and payments, plus the invoice 662 PDF output needed for document validation.

The full target workflow remains:

```text
Customer + Project + Time + Expense
-> Invoice Builder
-> Invoice 662 style PDF
-> Payment Application
-> Customer Balance
```

If that workflow is correct, the foundation is strong enough to expand.
