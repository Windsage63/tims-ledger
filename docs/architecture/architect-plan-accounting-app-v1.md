# Windsage Ledger - Architectural Blueprint

> **Engagement mode:** Greenfield
> **Date:** 2026-05-25
> **Status:** Draft with implementation status notes
> **Plan file:** plans/architect-plan-accounting-app-v1.md

## 1. Executive Summary

Build **Windsage Ledger**, a local-first accounting operations application for Air Advantage with the tagline **"Simple books I can understand."** The app replaces fragile spreadsheet accounting logic with a structured database, reliable invoice/payment workflows, and automation-ready records. The recommended architecture is a Python/FastAPI backend, React/TypeScript frontend, and SQLite database, designed first as a local browser app and later packageable as a desktop application if needed.

The guiding principle is to preserve the useful mental model of the current workbook while moving accounting truth into explicit records: customers, projects, time entries, expenses, invoices, payments, payment applications, credits, and audit checks.

## Implementation Status Snapshot

The architecture in this document is now partially validated by the checked-in codebase.

  - The FastAPI + SQLite + SQLAlchemy + Alembic backend is implemented and covered by automated tests for customer/project CRUD, source records, invoice creation and send, payment applications, customer balances, AR aging, workbook preview, receipt OCR review, backups, and the health endpoint.
  - The React + TypeScript frontend is implemented as an app shell with dashboard plus first create/list screens for customers, projects, time entries, expenses, and expense categories.
  - Invoice, payment, reporting, import, backup, and OCR user experiences are not yet wired into the React app, even where supporting backend endpoints already exist.
  - Invoice PDF generation, workbook import staging/commit, restore, packaging, and local password/PIN protection remain planned rather than implemented.

## 2. Context Discovery

### Existing Materials Reviewed

  - `Accounting Workbook Improvement Plan.md`
  - `Accounting Workbook Refined Requirements.md`
  - Original workbook analysis from `Timesheet Log and Project Tracking 2025.xlsx`
  - Google Stitch screen concepts for customers, projects, time tracking, invoice tracking, and invoice creation
  - User-provided `architect` skill package with blueprint template and discovery guidance

### Engagement Mode

This is a **greenfield** application. The workbook is not the target platform; it is the source of requirements, legacy data, and business rules. The first app milestone should prove that the application can reproduce one real invoice workflow correctly before attempting full replacement.

### Architect Skill Alignment

The provided architect skill aligns well with best practice for this effort. Its strengths are:

  - It separates architecture planning from implementation.
  - It requires ADR-style decisions and trade-off documentation.
  - It forces security, error handling, testing, deployment, and risks into the plan.
  - It keeps open questions visible instead of burying assumptions.

The only adjustment for this project is that we already have several decisions from prior discussion, so this blueprint starts with a recommended draft rather than a blank discovery questionnaire.

## 3. Technical Stack

| Layer | Technology | Rationale |
| ------- | ------------ | ----------- |
| Frontend | React + TypeScript + Vite | Best fit for a modern, stateful interface with reusable grids, forms, selectors, invoice builders, previews, and validation states. Vite keeps local development simple and fast. |
| Backend | Python + FastAPI | Matches user familiarity, supports typed API models, works well for spreadsheet import, accounting logic, PDF generation, OCR, parsing, and automation workflows. |
| Database | SQLite | Local-first, serverless, transactional, easy to back up as a single file, and appropriate for a small-business single-user or low-concurrency workflow. |
| ORM / Data Access | SQLAlchemy 2.x or SQLModel | Provides schema definition, migrations, relationships, and query abstraction while staying close to SQL. SQLModel may be simpler if Pydantic/FastAPI model sharing is preferred. |
| Migrations | Alembic | Standard migration path for SQLAlchemy-backed applications. |
| API Style | REST JSON | Simple, debuggable, works directly with FastAPI and React, and is adequate for the app's CRUD plus workflow actions. |
| UI System | Custom design system using Tailwind or CSS modules | Avoid generic SaaS templates; design dense, calm, work-focused accounting screens tailored to Air Advantage. |
| Data Grid | TanStack Table or equivalent | Needed for sortable/filterable time, expense, invoice, and payment tables without locking into a heavy enterprise grid immediately. |
| Forms | React Hook Form + Zod or Pydantic-derived validation strategy | Supports complex forms, validation feedback, and predictable input workflows. |
| PDF Output | Python PDF generation, likely WeasyPrint, ReportLab, or Playwright print-to-PDF | Invoices and reports must be printable and stable. Candidate should be chosen after a small invoice rendering spike. |
| Excel Import/Export | openpyxl / pandas | Python has mature tooling for importing the existing workbook and exporting accountant-friendly reports. |
| OCR Pipeline | Python service layer with pluggable OCR provider | Future receipt OCR is a strong reason to keep Python as the automation backend. Start with a provider interface, then choose local or cloud OCR later. |
| Packaging | Local browser app first; optional Tauri/Electron later | Prove the accounting model before desktop packaging. Tauri is attractive for smaller app size; Electron is easier if Node integration becomes central. |

## 4. Architectural Overview

### System Context

The application will initially run on the user's local Windows machine. A local FastAPI server owns the SQLite database and business rules. The React frontend runs in the browser and communicates with the backend over HTTP. Files such as receipts, imported workbooks, generated PDFs, and exports are stored in an application data directory and referenced from database records.

The app should be designed so that core business logic lives in Python services, not in the frontend. The frontend should guide workflows, present validation, and provide a polished working surface, but it should not be the source of accounting truth.

### Component Interaction

```text
React UI
  -> REST API calls
FastAPI API Layer
  -> Pydantic request/response validation
Application Services
  -> accounting rules, invoice generation, payment application, import/export, OCR pipeline
Repository Layer / ORM
  -> SQLite database
Filesystem Storage
  -> receipts, source imports, generated PDFs, exported reports
```

### Key Architectural Patterns

  - **Layered monolith:** One deployable app with clear internal layers. This is simpler and more maintainable than microservices for a small-business accounting tool.
  - **Workflow-oriented services:** Important operations such as invoice generation and payment application should be explicit service methods, not scattered CRUD updates.
  - **Audit-aware data model:** Records should preserve source, status changes, generated documents, and user approvals.
  - **Local-first storage:** The app should remain useful without cloud infrastructure.
  - **Automation-ready pipelines:** OCR, import, and report generation should be modeled as jobs even if the first implementation runs them synchronously.

## 5. Core Architectural Decisions

### ADR-1: Use Python/FastAPI for the Backend

Implementation status: validated in the current repository.

  - **Choice:** Python/FastAPI will own APIs, accounting logic, imports, exports, invoice generation, and future OCR.
  - **Rationale:** The hardest parts are data extraction, reconciliation, document generation, and automation. Python is stronger for these than Node in this context, and it matches the user's experience.
  - **Alternatives considered:** Node/Express, Node/NestJS, full-stack React framework.
  - **Trade-offs:** A React frontend plus Python backend means two runtimes and a little more project setup. The trade is worth it because Python reduces risk in the business logic layer.

### ADR-2: Use React/TypeScript for the Frontend

Implementation status: validated for the app shell and first source-record screens; richer workflow screens remain planned.

  - **Choice:** Build the UI in React with TypeScript.
  - **Rationale:** The app needs rich screens: invoice builder, editable grids, filters, receipt review, payment application, and live invoice preview. React is a strong fit for reusable UI components and stateful workflows.
  - **Alternatives considered:** Plain HTML/JS, server-rendered Jinja/HTMX, desktop-native UI.
  - **Trade-offs:** React adds build tooling and frontend complexity. In return, it gives a more maintainable interface for the level of interactivity required.

### ADR-3: Start with SQLite

Implementation status: validated in the current repository.

  - **Choice:** Use SQLite as the primary database for MVP.
  - **Rationale:** The app is local-first, single-user or low-concurrency, and benefits from simple backup/restore. SQLite is transactional and avoids database server administration.
  - **Alternatives considered:** PostgreSQL, DuckDB, flat files.
  - **Trade-offs:** SQLite is not ideal for many simultaneous users over a network share. If multi-user access becomes a requirement, plan a migration path to PostgreSQL.

### ADR-4: Treat Invoices and Payments as Separate Accounting Records

Implementation status: validated in the current repository.

  - **Choice:** Store invoices, payments, and payment applications as separate first-class entities.
  - **Rationale:** Customer advances, partial payments, overpayments, and multi-invoice checks cannot be modeled reliably with one running-balance sheet.
  - **Alternatives considered:** Single ledger table only, invoice table with embedded payment fields.
  - **Trade-offs:** More tables and workflows, but this is the core structure needed for reliable customer balances.

### ADR-5: Generate Invoices from Source Records, Not Manual Lines

Implementation status: partially validated. Draft invoice creation and send/finalize from source records are implemented in the backend; preview, grouping controls, and PDF output remain planned.

  - **Choice:** Invoice builder should select approved unbilled time, eligible billable expenses, and approved non-hourly or fixed-fee billing lines, then generate invoice line items.
  - **Rationale:** Manual invoice entry would be a regression from the automated invoicing currently in place in the spreadsheet. The app should support editable invoices that can be issued, recalled to draft, revised, and reissued without introducing bookkeeping steps that do not add value in a single-user workflow.
  - **Alternatives considered:** Blank invoice editor, direct PDF editing, spreadsheet-style row formulas.
  - **Trade-offs:** This approach is less intentionally less audit-rigid than typical enterprise accounting controls. Since there is noone to read the audit trail, it would simply be a waste of code.

### ADR-6: Design Receipt OCR as a Pipeline, Not a One-Off Feature

Implementation status: partially validated. File capture, OCR job records, suggestion updates, and approval into expenses exist; provider-backed OCR automation and frontend review UX remain planned.

  - **Choice:** Receipt OCR should be modeled as upload -> extraction -> suggested expense -> review -> approval.
  - **Rationale:** OCR is probabilistic. The app must store raw extracted data separately from approved accounting fields.
  - **Alternatives considered:** Directly create expenses from OCR output.
  - **Trade-offs:** Review workflow adds steps, but it protects accounting data quality.

## 6. Component Breakdown

| Component | Description | Priority | Dependencies | Current Status |
| ----------- | ------------- | ---------- | -------------- | ---------------- |
| App Shell / Navigation | Shared layout, navigation, global search, settings access. | P0 | Frontend foundation | Implemented in React; later sections still placeholders. |
| Customers | Customer master records, terms, contacts, balance summaries. | P0 | Database, API | Backend CRUD implemented and tested; frontend has first create/list screen. |
| Projects | Project records, rates, contract type, fixed-fee settings, and customer association. | P0 | Customers | Backend CRUD implemented and tested; frontend has first create/list screen. |
| Time Entries | Time logging, billing status, project rates, unbilled tracking. | P0 | Projects, Customers | Backend implemented and tested; frontend has first create/list screen. |
| Expenses | Expense entry, categories, billable/reimbursable flags, paid-by, receipt attachment. | P0 | Projects, Customers, Categories | Backend implemented and tested; frontend has first expense and category create/list screens. |
| Invoice Builder | Select eligible source records and approved non-hourly lines, build an editable draft, preview totals, and issue the invoice. | P0 | Time, Expenses, Customers, Projects | Backend candidate lookup and draft creation implemented; frontend workflow not started. |
| Invoice Register | One row per invoice with sent/draft/paid/overdue status and open balance. | P0 | Invoice Builder, Payments | Backend list/detail implemented; frontend workflow not started. |
| Payments | Record deposits, customer advances, checks, payment methods, unapplied amounts. | P0 | Customers | Backend implemented and tested; frontend workflow not started. |
| Payment Applications | Apply payments/credits to invoices, support partial and multi-invoice applications. | P0 | Payments, Invoices | Backend implemented and tested; frontend workflow not started. |
| Customer Balance | AR, credits, invoice history, payment history, net balance by customer. | P0 | Invoices, Payments | Backend summary implemented and tested; frontend workflow not started. |
| Reports | AR aging, revenue by customer/project, expense category export, tax/accounting export. | P1 | Core accounting records | AR aging and CSV exports implemented; broader reporting remains planned. |
| Workbook Import | Import customers, projects, time, expenses, and income tracking from legacy workbook. | P1 | Data model, validation | Workbook preview implemented; staging and commit remain planned. |
| PDF Invoice Output | Generate printable invoice PDFs from invoice records. | P1 | Invoice Builder | Not yet implemented. |
| Receipt OCR | Upload receipt, extract fields, review suggestions, create expense, and preserve receipt images for later invoice attachment. | P2 | Expenses, file storage | Backend job/review flow implemented; provider integration and frontend review queue remain planned. |
| Backup / Restore | Copy/export database and attached files safely. | P1 | Storage layer | Backup creation implemented; restore remains planned. |
| Audit Log | Track material changes to invoices, payments, applications, and approved expenses. | P1 | Core services | Schema exists; feature behavior is not yet surfaced. |

## 7. Data Architecture

### Storage Model

  - SQLite database stores structured records.
  - Filesystem stores receipts, imported workbooks, generated invoices, and exported reports.
  - Database stores file metadata and relative paths, not large binary blobs for MVP.
  - Migrations are versioned through Alembic.

### Core Schema

| Entity | Purpose | Key Fields |
| -------- | --------- | ------------ |
| `customers` | Customer master data. | id, name, billing_email, phone, default_terms, active, notes |
| `projects` | Project master data and billing rules. | id, project_no, customer_id, name, description, contract_type, status, default_rate, rates, fixed_fee_amount |
| `time_entries` | Billable and nonbillable work. | id, date, project_id, customer_id, description, hours, work_type, rate, billable, billing_status, invoice_id |
| `expense_categories` | Operational and accounting category mapping. | id, name, default_billable, default_reimbursable, tax_category, revenue_category, expense_category |
| `expenses` | Expense records and reimbursement metadata. | id, date, project_id, customer_id, vendor, description, qty, unit_cost, total, category_id, billable, reimbursable, paid_by, payment_method, reimbursement_status, invoice_id, receipt_file_id |
| `invoices` | Accrual revenue record. | id, invoice_no, customer_id, invoice_date, sent_date, due_date, status, terms, subtotal_labor, subtotal_expenses, freight, per_diem, other, sales_tax, total, open_balance |
| `invoice_lines` | Printable/detail lines for invoices, including linked source rows and approved non-hourly billing lines. | id, invoice_id, source_type, source_id, description, qty, unit_price, amount, line_group, sort_order |
| `payments` | Cash receipts and customer credits. | id, customer_id, payment_date, deposit_date, payment_type, reference_no, amount_received, unapplied_amount, bank_account, notes |
| `payment_applications` | Application of payments/credits to invoices. | id, payment_id, invoice_id, application_date, amount_applied, notes |
| `files` | Attached/imported/generated files. | id, file_type, original_name, storage_path, mime_type, sha256, created_at |
| `ocr_jobs` | Receipt OCR pipeline status. | id, file_id, status, provider, extracted_json, confidence, reviewed_by, reviewed_at |
| `audit_events` | Material change history. | id, entity_type, entity_id, action, before_json, after_json, created_at |
| `app_settings` | Company info, invoice defaults, numbering. | key, value_json |

### Critical Data Flows

#### Invoice Generation

1. User opens Invoice Builder for a customer/project.
2. Backend returns eligible unbilled billable time, eligible expenses, and any approved non-hourly billing candidates for the selected project.
3. User includes or excludes rows, reviews draft totals, and sees prior balance and unapplied credits separately from the new invoice charges.
4. Backend creates a draft invoice and invoice lines in one transaction.
5. While the invoice remains in draft, the user may revise the selected rows before issuance.
6. When the user sends or finalizes the invoice, invoice status becomes `issued`, accrual revenue is recognized, and the included source rows are marked with that invoice number.
7. Issued invoices are viewable and printable, and may be recalled to draft mode through an edit control for correction and reissue.
8. Recalling an invoice removes its current invoice lines from the invoice record and clears that invoice number from the previously assigned time and expense rows.
9. A recalled invoice then behaves like a normal draft again, so reissue rebuilds the invoice from the newly selected source rows.
10. Previously generated PDF output may remain stored for reference, and newly generated PDF output replaces the working invoice document on reissue.

#### Payment Application

1. User records a payment or advance for a customer.
2. Payment starts with full `unapplied_amount`.
3. User applies all or part of payment to one or more open invoices.
4. Backend creates `payment_applications` and recalculates invoice open balances and payment unapplied balance in one transaction.
5. Unapplied credits remain separate from invoice line items and affect balances only through payment application logic.
6. Invoice statuses update to paid, partially paid, overdue, or sent as appropriate.

#### Receipt OCR

1. User uploads receipt image/PDF.
2. File is stored and an OCR job is created.
3. OCR extracts merchant, date, amount, tax, payment method, and candidate category.
4. Extracted data is displayed as suggestions, not final accounting data.
5. User approves or edits suggestions.
6. Approved result creates or updates an expense record and attaches the receipt file.
7. If that expense is later billed, the receipt image may be appended to the generated invoice PDF.

### Migration Strategy

  - MVP starts with clean schema migration `0001_initial`.
  - Current implementation supports workbook preview; staged import and commit remain planned.
  - Imports should preserve original row references so discrepancies can be traced.
  - Schema changes must be additive where possible.
  - Before destructive schema migrations, create automatic backup of the SQLite database.

## 8. API Design

### Conventions

  - REST JSON endpoints under `/api`.
  - Use plural resources: `/api/customers`, `/api/projects`.
  - Workflow actions are explicit subroutes: `/api/invoices/{id}/send`, `/api/payments/{id}/apply`.
  - Responses include stable IDs and calculated display fields where useful.
  - Errors use a consistent shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invoice cannot be sent with no line items.",
    "details": []
  }
}
```

### Key Endpoints

| Method | Path | Purpose |
| -------- | ------ | --------- |
| GET | `/api/customers` | List/search customers. |
| POST | `/api/customers` | Create customer. |
| GET | `/api/customers/{id}` | Customer detail. |
| GET | `/api/customers/{id}/balance` | Customer balance summary. |
| GET | `/api/projects` | List/search projects. |
| POST | `/api/projects` | Create project and rates. |
| GET | `/api/time-entries` | List/filter time entries. |
| POST | `/api/time-entries` | Create time entry. |
| GET | `/api/expenses` | List/filter expenses. |
| POST | `/api/expenses` | Create expense. |
| GET | `/api/expense-categories` | List expense categories. |
| POST | `/api/expense-categories` | Create expense category. |
| POST | `/api/receipts` | Upload receipt file and optionally start OCR. |
| GET | `/api/ocr-jobs/{id}` | Read OCR job state. |
| PATCH | `/api/ocr-jobs/{id}/suggestions` | Store OCR suggestions for review. |
| POST | `/api/ocr-jobs/{id}/review` | Approve OCR suggestions into an expense. |
| GET | `/api/invoice-builder/candidates` | Return unbilled time/expenses for customer/project. |
| POST | `/api/invoices` | Create draft invoice from selected records. |
| GET | `/api/invoices` | List invoices. |
| GET | `/api/invoices/{id}` | Read invoice detail. |
| POST | `/api/invoices/{id}/send` | Finalize/send invoice and recognize accrual revenue. |
| POST | `/api/invoices/{id}/recall` | Return an issued invoice to draft mode, remove current invoice lines, and clear source-record invoice assignments for reissue. |
| POST | `/api/payments` | Record payment/advance. |
| POST | `/api/payments/{id}/applications` | Apply payment to one or more invoices. |
| GET | `/api/reports/ar-aging` | AR aging report. |
| GET | `/api/reports/ar-aging.csv` | Download AR aging CSV. |
| GET | `/api/reports/open-invoices.csv` | Download open invoices CSV. |
| POST | `/api/imports/workbook/preview` | Preview workbook sheets and mapping hints. |
| POST | `/api/backups` | Create a local backup zip. |

## 9. Security Architecture

### Threat Model

This is initially a local app handling business financial data, customer contact information, receipts, and possibly tax-relevant records. Trust boundaries are:

  - Browser to local API.
  - API to SQLite database.
  - API to local filesystem.
  - Optional future OCR provider boundary if cloud OCR is used.

### Authentication and Authorization

For MVP, use local-only authentication mode:

  - App binds to `127.0.0.1` by default.
  - Optional local password/PIN can be added before real financial use.
  - Roles are not needed for single-user MVP, but model future roles as `owner/admin`, `bookkeeper`, and `viewer`.

### Data Protection

  - Store database and files in a known application data directory.
  - Provide backup/export function early.
  - Never expose the FastAPI server on the network by default.
  - Validate all inputs through Pydantic.
  - Sanitize uploaded filenames and store files under generated names.
  - Use file hashes to detect duplicate receipt uploads.
  - If cloud OCR is later used, surface that data leaves the local machine.

### Compliance

No formal compliance target for MVP. Treat as sensitive internal financial data. Avoid storing bank credentials or payment card data.

## 10. Error Handling & Resilience

| Failure | Detection | Recovery |
| --------- | ----------- | ---------- |
| Invoice generation fails halfway | Transaction rollback | No invoice issuance or source-row invoice assignment is persisted unless the relevant transaction succeeds. |
| Payment application exceeds invoice/payment balance | Service-level validation | Reject transaction with clear message. |
| Receipt OCR fails | OCR job status becomes `failed` | User can manually enter expense or retry OCR. |
| Imported workbook has inconsistent data | Import validation report | Import into staging and require user review before commit. |
| PDF generation fails | Exception captured with invoice id | Invoice remains valid; user can retry PDF generation. |
| Database corruption or bad migration | Startup health check / migration failure | Restore from latest backup; migrations create backup first. |
| File attachment missing | File existence check | Show missing-file warning without breaking accounting record. |

### Resilience Patterns

  - Use database transactions for invoice creation and payment application.
  - Use idempotency keys or duplicate detection for import and file upload later.
  - Store generated documents as reproducible outputs tied to source invoice data.
  - Maintain validation checks as first-class backend routines, not only UI warnings.

## 11. Testing Strategy

| Level | Scope | Tools | Coverage Target |
| ------- | ------- | ------- | ----------------- |
| Unit | Accounting calculations, invoice status logic, payment application rules, OCR parsing helpers. | pytest | High coverage on accounting services. |
| Integration | API endpoints with SQLite test database and filesystem temp directory. | pytest + FastAPI TestClient | Core workflows covered. |
| Frontend Unit | Component behavior for forms, tables, filters, status displays. | Vitest + React Testing Library | Critical UI components. |
| E2E | Time/expense -> invoice -> payment -> customer balance. | Playwright | MVP workflow must pass. |
| Import Tests | Legacy workbook samples and known invoices such as invoice 662. | pytest fixtures | Deterministic reconciliation tests. |

### Golden Test Workflow

Current status: the backend test suite covers the invoice creation, send/finalize, payment application, balance, import preview, OCR review, and backup slices. The full invoice 662 PDF validation workflow is still pending because PDF output and import staging are not yet implemented.

The first acceptance test should reproduce a known real workflow:

```text
Import customer/project/time/expenses for invoice 662
-> build invoice
-> verify invoice total and printed lines
-> record payment
-> apply payment
-> verify customer balance
```

## 12. Performance & Scaling

### Expected Load

  - Initial users: 1 primary user, possibly one bookkeeper/accountant later.
  - Data volume: thousands to tens of thousands of time/expense/payment records, not millions.
  - Attachments: receipts and PDFs may become the largest storage component.

### Optimization Strategy

  - Add indexes on invoice number, customer id, project id, dates, status, and foreign keys.
  - Paginate tables by default.
  - Use backend filters rather than loading all records into the browser.
  - Keep OCR and import operations as jobs if they become slow.

### Known Bottlenecks

  - Workbook import and OCR may be slower than standard CRUD.
  - PDF generation can be slow if rendering many invoices at once.
  - Large receipt directories require file cleanup and backup planning.

## 13. Deployment & Infrastructure

### Runtime Environment

MVP runs locally:

```text
FastAPI server on 127.0.0.1
React dev/build assets served by local frontend server during development
SQLite database in app data directory
Receipts/PDFs in app-managed file storage
```

### Environments

| Environment | Purpose | Key Differences |
| ------------- | --------- | ----------------- |
| Development | Build and test locally. | Hot reload, test database, verbose logging. |
| Test | Automated tests. | Temporary SQLite and file directories. |
| Production Local | Real business use on local machine. | Persistent database/files, backups, network binding disabled. |

### Packaging Path

1. Start as local web app.
2. Add single command launcher script.
3. Later evaluate packaging:
   - Tauri if small desktop bundle and security are priorities.
   - Electron if Node/native desktop integration becomes easier or more important.

## 14. Requirements & Acceptance Criteria

### Functional Requirements

  - [ ] FR-1: Users can create and manage customers.
  - [ ] FR-2: Users can create and manage projects with customer, status, contract type, and rates.
  - [ ] FR-3: Users can enter time against projects and classify it as billable or nonbillable.
  - [ ] FR-4: Users can enter expenses with category, billable/reimbursable flags, paid-by, payment method, and receipt attachment.
  - [ ] FR-5: Users can build editable draft invoices from selected unbilled time, eligible expenses, and approved non-hourly billing lines.
  - [ ] FR-6: Issuing/finalizing an invoice marks the included source records with that invoice number, and an edit button can recall the invoice to draft mode, remove its current invoice lines, clear those source-record invoice assignments, and allow normal reissue.
  - [ ] FR-7: Users can record payments and customer advances independent of invoices.
  - [ ] FR-8: Users can apply one payment to multiple invoices and multiple payments to one invoice.
  - [ ] FR-9: Customer balances show open AR, unapplied credits, net balance, invoice history, and payment history.
  - [ ] FR-10: App can generate printable invoice PDFs.
  - [ ] FR-11: App can import relevant records from the existing workbook or a staging export.
  - [ ] FR-12: App can export accountant-friendly reports to Excel/CSV.

Implementation note:

  - FR-1 through FR-9 are largely satisfied in the backend, with partial frontend coverage for FR-1 through FR-4.
  - FR-10 is still open.
  - FR-11 is partially satisfied through workbook preview only.
  - FR-12 is partially satisfied through CSV exports only.

### Non-Functional Requirements

  - [ ] NFR-1: The app must not require internet access for core accounting workflows.
  - [ ] NFR-2: Core accounting operations must be transactionally safe.
  - [ ] NFR-3: The database and attachments must be easy to back up.
  - [ ] NFR-4: The UI must support dense data review without feeling like a marketing dashboard.
  - [ ] NFR-5: Accounting validation errors must be visible before records are finalized.
  - [ ] NFR-6: OCR output must require review before becoming approved accounting data.

## 15. Implementation Roadmap

### Phase 0: Product Blueprint and Data Model

1. Finalize data model and workflow map.
2. Choose SQLAlchemy vs SQLModel.
3. Choose UI design direction and component library strategy.
4. Define invoice 662 as the first golden test case.

### Phase 1: Core Local App Foundation

1. Create FastAPI project structure.
2. Create React/TypeScript frontend structure.
3. Add SQLite connection, migrations, and settings.
4. Implement app shell and navigation.
5. Add customers and projects CRUD.

Current status: complete for backend and first React create/list screens.

### Phase 2: Source Records

1. Implement time entry model, API, table, and form.
2. Implement expense model, API, table, and form.
3. Add category setup and rate lookup.
4. Add receipt file attachment storage without OCR.

Current status: source-record APIs and first React screens are in place. Receipt handling has moved past this phase into a basic OCR job/review backend flow.

### Phase 3: Invoice Workflow

1. Implement invoice candidate selection.
2. Implement draft invoice creation from selected source rows.
3. Implement invoice preview and line grouping.
4. Implement send/finalize and recall-to-draft workflow.
5. Generate PDF invoice.
6. Validate against invoice 662.

Current status: steps 1, 2, and issue/finalize are implemented in the backend. Recall and reissue behavior, UI workflow, PDF output, and invoice 662 validation remain open.

### Phase 4: Payments and Customer Balances

1. Implement payments and customer advances.
2. Implement payment applications.
3. Implement customer balance detail.
4. Implement AR aging and open invoice reports.
5. Add validation dashboard/checks.

Current status: steps 1 through 4 are implemented in the backend. React screens remain open.

### Phase 5: Workbook Migration and Reporting

1. Build workbook import staging.
2. Map existing customers, projects, time, expenses, income tracking.
3. Produce discrepancy report.
4. Export accountant reports.

Current status: workbook preview plus AR aging and open invoice CSV exports exist; staging, discrepancy reporting, and broader export coverage remain open.

### Phase 6: Automation Layer

1. Add OCR job table and receipt review screen.
2. Integrate chosen OCR provider.
3. Add expense suggestions and confidence scoring.
4. Add batch import or email-forwarded receipts later if useful.

Current status: OCR jobs and approval into expenses are implemented in the backend without provider automation or dedicated frontend review screens.

### Phase 7: Packaging and Hardening

1. Add backup/restore.
2. Add local password/PIN if desired.
3. Add installer/launcher.
4. Evaluate Tauri/Electron packaging.

Current status: backup creation exists; restore, packaging, and local authentication remain open.

## 16. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
| ------ | ------------ | -------- | ------------ |
| Spreadsheet business rules are more nuanced than documented. | High | High | Use real invoice 662 and several edge cases as golden tests before broad migration. |
| Invoice PDF does not match business expectations. | Medium | High | Build invoice preview/PDF early and validate against current printed invoice. |
| Payment/credit model mishandles advances. | Medium | High | Implement payments and applications as separate tables with transaction tests. |
| OCR creates bad accounting records. | Medium | Medium | Store OCR suggestions separately and require user approval. |
| React frontend becomes overbuilt. | Medium | Medium | Keep MVP screens dense and workflow-focused; defer decorative dashboards. |
| SQLite limits if multi-user access is needed. | Low initially, higher later | Medium | Keep repository layer portable; design schema that can migrate to PostgreSQL. |
| Local files become disorganized. | Medium | Medium | Centralize file storage with database metadata, hashes, and backup support. |
| User trust drops if import produces unexpected numbers. | Medium | High | Show import reconciliation reports and never overwrite source workbook. |

## 17. Open Questions

  - [ ] Should advance payments be tracked only at the customer level, or optionally reserved for a specific project before invoicing?
  - [ ] Should one invoice be allowed to include multiple projects, or should invoice-to-project remain one-to-one?
  - [ ] Should fixed-fee project costs appear on invoices, internal project profitability only, or both depending on category?
  - [ ] Should fixed-fee or HD billing lines be modeled as a dedicated source-record type, or only as controlled invoice-draft lines?
  - [ ] While an invoice is in draft, should selected source rows be reserved from other drafts, or remain generally eligible until issuance?
  - [ ] Should unapplied credits be applied during the invoice issue workflow, or only through a separate payment-application step after the invoice exists?
  - [ ] Should owner/employee expense reports be first-class records in this app or summarized from separate expense reports?
  - [ ] Should the MVP include local password protection, or is local machine access control enough for the first version?
  - [ ] Which invoice PDF approach should be selected after a rendering spike?
  - [ ] Should generated invoice numbers continue as simple sequential numbers only, or include a display/reference field such as `250507-0662`?
  - [ ] What is the desired backup location and backup frequency?
  - [ ] Should OCR be local-only, cloud-assisted, or provider-pluggable with user choice?
  - [ ] When billed receipts are appended to an invoice PDF, which expense categories require attachment and in what order should attachments appear?

## 18. Recommended Next Step

The next step is still not to build every screen. It is to finish the narrow proof-of-architecture by wiring the existing backend workflows into the React app and adding invoice PDF output:

```text
Customer + Project + Time + Expense
-> Invoice Builder
-> Invoice 662 PDF
-> Payment Application
-> Customer Balance
```

If that workflow reproduces the existing invoice and fixes customer balance tracking, the architecture is validated.
