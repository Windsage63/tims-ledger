# Windsage Ledger

**Simple books I can understand.**

Windsage Ledger is a local-first accounting operations app for project-driven consulting work. The goal is to replace fragile spreadsheet accounting logic with a structured, understandable system for customers, projects, time, expenses, invoices, payments, credits, and reports.

## Current Status

This repository is in early architecture and project setup. The source workbook, Stitch screen concepts, and planning documents are included as references so the app can be designed around the actual Air Advantage workflow rather than a generic accounting template.

## Planned Stack

  - Backend: Python, FastAPI, SQLite, SQLAlchemy or SQLModel
  - Frontend: React, TypeScript, Vite
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
docs/product/        Product workflow, UX, and screen planning
references/          Source workbook and Stitch design references
```

## First Proof Workflow

The first technical milestone should prove this end-to-end workflow:

```text
Customer + Project + Time + Expense
-> Invoice Builder
-> Invoice 662 style PDF
-> Payment Application
-> Customer Balance
```

If that workflow is correct, the foundation is strong enough to expand.
