# Winds Ledger Architecture Plan v1

## Executive Summary

Winds Ledger will be built as a small, single-user, file-backed accounting application for a consulting engineering practice. The system will use a local SQLite database file for durable relational storage, a FastAPI backend for data integrity and bookkeeping operations, and a vanilla HTML/CSS/JS frontend for responsive behavior without React.

The architecture is intentionally conservative. The goal is to replace spreadsheet-driven bookkeeping with a traceable system for customers, projects, time, expenses, invoices, invoice ledgering, and payment tracking, while avoiding infrastructure that belongs to larger multi-user products.

## Engagement Mode

1. Greenfield application from a code perspective.
2. Existing repo artifacts are requirements and reference screens only.
3. Latest explicit user decisions override older draft wording when they conflict.

## Source Priority

1. Latest explicit user decisions in conversation.
2. [docs/winds_ledger_prd.md](../docs/winds_ledger_prd.md).
3. [docs/workflows.md](../docs/workflows.md).
4. Stitch HTML screens as presentation references only.

## Confirmed Product Decisions

1. There will be no manual invoice lines.
2. Fixed-fee billing is represented as a one-hour time entry with a custom rate equal to the fixed-fee amount.
3. A single computer will operate at one time.
4. Human-readable output is for inspection, not as an editable source of truth.
5. v1 runs in a local browser against FastAPI.
6. v1 has no login.
7. Invoice PDFs are generated server-side.
8. Backup and restore are in scope for v1.
9. XLSX audit export is in scope for v1.
10. Spreadsheet import is not required in v1.

## System Goals

1. Replace spreadsheet bookkeeping with a durable relational file.
2. Keep bookkeeping traceable from source entry through invoice and payment application.
3. Preserve a live, responsive user interface without React complexity.
4. Make invoice ledger and payment tracking first-class parts of the system.
5. Stay small enough that the implementation remains understandable to one developer.

## Non-Goals

1. Multi-user concurrency.
2. Cloud-native or browser-only offline storage.
3. Enterprise accounting breadth such as bank feeds, payroll, or general ledger modules.
4. Recreating QuickBooks or SAP.
5. Spreadsheet-as-database workflows.

## Technical Stack

### Backend

1. Python 3.x.
2. FastAPI for routes, API endpoints, validation boundaries, and bookkeeping operations.
3. Standard `sqlite3` library in v1.
4. Raw SQL or very thin query helpers instead of an ORM.

### Frontend

1. Server-served HTML pages with a shared shell.
2. Vanilla JavaScript for live interactions.
3. Tailwind CSS for layout and styling.
4. Jinja templates only for the initial page shell and shared layout, not for live interaction updates.

### Data Storage

1. Single SQLite database file as the primary system of record.
2. Database backup and restore as file operations.
3. XLSX export for audit and human inspection only.

### Document Generation

1. Server-side invoice PDF generation from controlled HTML templates.
2. Printable invoice layout derived from the same source-linked data model used in the UI.

## Architectural Decisions

### ADR-001: Use SQLite As The Primary Datastore

Decision: Store all application data in a single SQLite file.

Rationale: The system needs separate tables, keys, constraints, and file portability without the overhead of a network database.

Trade-offs: The approach gives a durable file, strong relational support, and a small operational footprint, but it is not suitable for concurrent multi-user editing or shared live access across multiple computers.

### ADR-002: Use FastAPI As A Thin Backend

Decision: Use FastAPI for API routes, validation boundaries, PDF generation, and bookkeeping operations.

Rationale: The application needs a backend for file-backed storage, transactional updates, and document generation, but does not need a heavy service architecture.

Trade-offs: The approach gives clean routing and typed request handling, but it introduces server-side runtime and packaging concerns compared with a pure static app.

### ADR-003: Use Vanilla JS Instead Of React

Decision: Use vanilla JavaScript for dynamic page behavior and local in-memory table filtering.

Rationale: The user already has success with HTML/JS-first applications and found React too costly for a small internal workflow tool.

Trade-offs: The approach keeps cognitive overhead low and aligns well with the Stitch HTML references, but it requires discipline in page module structure because there is no framework enforcing boundaries.

### ADR-004: Keep Jinja Thin

Decision: Use Jinja only for shared layout, page shell rendering, and initial payload embedding where useful.

Rationale: Previous experience showed friction when live behavior depended on Python-rendered template refreshes.

Trade-offs: This keeps layout reuse without turning Python templates into the interaction engine, but it requires a clean API contract between page JS and backend JSON endpoints.

### ADR-005: Backend Owns Bookkeeping Truth, Frontend Owns Interaction State

Decision: Load working tables into page-local JS state for filtering and responsiveness, but keep bookkeeping truth on the backend.

Rationale: At roughly 1,000 transactions per year, page-local filtering is inexpensive and improves responsiveness.

Trade-offs: The UI stays live and responsive, but writes must always return to the backend and JS must not become a second bookkeeping engine.

### ADR-006: No Manual Invoice Lines

Decision: Every billed amount must originate from a source time entry or expense entry.

Rationale: This keeps the system simple and fully traceable.

Trade-offs: Auditability improves and invoice logic stays small, but any exceptional billing pattern must still be represented as a proper source record.

### ADR-007: Fixed-Fee Billing Uses One-Hour Custom-Rate Time Entries

Decision: Fixed-fee billing will be represented as time entries with one hour and a custom rate equal to the fee amount.

Rationale: This removes the need for manual invoice lines or a separate fixed-fee billing subsystem.

Trade-offs: The billing model stays unified and traceable, but the UI and documentation must clearly explain what those one-hour fixed-fee entries mean.

### ADR-008: No Login In v1

Decision: v1 will assume a trusted local-user environment with no login.

Rationale: The application runs on a single active computer and does not need account management overhead.

Trade-offs: The local experience stays simple, but there is no application-level separation of users or permissions.

## System Context

### Primary User

1. A small consulting engineering practice.
2. Low transaction volume.
3. High need for year-end correctness and traceable payment status.

### Core Business Problem

The current spreadsheet workflow is good enough for recording time and expenses and manually linking invoice numbers, but it breaks down around invoice ledgering, payment application, open balances, and year-end reconciliation. The new system exists to solve those bookkeeping gaps without creating software heavier than the business itself.

## Component Breakdown

### 1. Web Application Shell

Responsibility: shared layout, navigation, static assets, route entry pages.

Priority: High.

Dependencies: FastAPI, Tailwind, page JS modules.

### 2. Customers Module

Responsibility: customer create, edit, browse, and account summary.

Priority: High.

Dependencies: `customers`, invoice aggregates, payment aggregates.

### 3. Projects Module

Responsibility: project setup, customer linkage, and rate management.

Priority: High.

Dependencies: `projects`, `project_rates`, `customers`.

### 4. Time Module

Responsibility: time entry, filtering, and invoice linkage display.

Priority: High.

Dependencies: `time_entries`, `projects`, `customers`, `project_rates`.

### 5. Expenses Module

Responsibility: expense entry, filtering, billable state, and invoice linkage display.

Priority: High.

Dependencies: `expenses`, `projects`, `customers`.

### 6. Invoice Builder And Invoice Ledger

Responsibility: create and edit invoices by selecting eligible time and expenses, generate PDFs, and maintain the issued invoice ledger.

Priority: High.

Dependencies: `invoices`, `time_entries`, `expenses`, `customers`, `projects`.

### 7. Payments Ledger And Application Module

Responsibility: record payments, track unapplied amounts, apply payments to invoices, and compute open balances.

Priority: High.

Dependencies: `payments`, `payment_applications`, `invoices`, `customers`.

### 8. Reporting And Export Utilities

Responsibility: XLSX audit export, backup and restore, and integrity checks.

Priority: Medium.

Dependencies: all ledger tables.

## Data Architecture

### Database Principles

1. The SQLite file is the only source of truth.
2. Financial balances are derived, not hand-maintained.
3. Links between source records and invoices are stored explicitly.
4. Updates that touch multiple tables run inside explicit transactions.
5. Foreign keys must be enabled on every database connection.

### Core Tables

#### customers

Purpose: customer master records.

Candidate fields:

1. `id`
2. `customer_name`
3. `street_address`
4. `city`
5. `state`
6. `zip`
7. `contact_name`
8. `email`
9. `phone`
10. `notes`
11. `created_at`
12. `updated_at`

#### projects

Purpose: project master records linked to customers.

Candidate fields:

1. `id`
2. `project_number`
3. `customer_id`
4. `description`
5. `default_rate_cents`
6. `created_at`
7. `updated_at`

#### project_rates

Purpose: per-project rate codes and rate values.

Candidate fields:

1. `id`
2. `project_id`
3. `rate_code`
4. `rate_cents`
5. `is_builtin`
6. `sort_order`
7. `created_at`
8. `updated_at`

#### time_entries

Purpose: time source records.

Candidate fields:

1. `id`
2. `entry_date`
3. `project_id`
4. `customer_id` cached for convenience or derived only by join
5. `description`
6. `minutes`
7. `rate_code`
8. `rate_cents`
9. `line_total_cents`
10. `invoice_id` nullable
11. `created_at`
12. `updated_at`

#### expenses

Purpose: expense source records.

Candidate fields:

1. `id`
2. `entry_date`
3. `project_id`
4. `customer_id` cached for convenience or derived only by join
5. `vendor`
6. `description`
7. `quantity`
8. `unit_cost_cents`
9. `line_total_cents`
10. `category`
11. `is_billable`
12. `invoice_id` nullable
13. `created_at`
14. `updated_at`

#### invoices

Purpose: invoice headers and metadata.

Candidate fields:

1. `id`
2. `invoice_number`
3. `project_id`
4. `customer_id`
5. `invoice_date`
6. `terms_days`
7. `notes` nullable
8. `pdf_path` or equivalent file reference
9. `issued_at` nullable
10. `updated_at`

#### payments

Purpose: customer payment records, including unapplied balances awaiting allocation.

Candidate fields:

1. `id`
2. `customer_id`
3. `payment_date`
4. `reference_number` nullable
5. `amount`
6. `notes` nullable
7. `created_at`
9. `updated_at`

#### payment_applications

Purpose: allocations from payments to invoices.

Candidate fields:

1. `id`
2. `payment_id`
3. `invoice_id`
4. `applied_amount`
5. `applied_at`

### Relationship Model

1. `projects.customer_id -> customers.id`
2. `project_rates.project_id -> projects.id`
3. `time_entries.project_id -> projects.id`
4. `expenses.project_id -> projects.id`
5. `time_entries.invoice_id -> invoices.id` nullable
6. `expenses.invoice_id -> invoices.id` nullable
7. `invoices.project_id -> projects.id`
8. `invoices.customer_id -> customers.id`
9. `payments.customer_id -> customers.id`
10. `payment_applications.payment_id -> payments.id`
11. `payment_applications.invoice_id -> invoices.id`

### Derived Financial Rules

1. Invoice amount equals the sum of linked time entries plus the sum of linked expenses.
2. Invoice paid amount equals the sum of payment applications linked to that invoice.
3. Invoice open balance equals invoice amount minus invoice paid amount.
4. Payment unapplied amount equals payment amount minus the sum of its applications.
5. Customer open AR equals the sum of open invoice balances for that customer.
6. Customer unapplied credit equals the sum of payment unapplied amounts for that customer.
7. Customer net balance must be a clearly defined derived display value rather than a hand-maintained stored field.

### Migration Strategy

1. v1 does not require spreadsheet import as a planned product feature.
2. Initial data entry may be manual or handled by a one-off migration utility outside the first implementation phase.
3. The schema should still support a later import tool without redesign.

## API Design

### Page Delivery

FastAPI serves page routes for the major screens and static assets for CSS and JS.

Examples:

1. `GET /customers`
2. `GET /projects`
3. `GET /time`
4. `GET /expenses`
5. `GET /invoices`
6. `GET /payments`

### JSON API Principles

1. Screen JS modules load the relevant working dataset from JSON endpoints.
2. Filtering, sorting, selection state, and view-level convenience calculations happen in page-local JS.
3. Data mutations always go through the API.
4. API responses return authoritative saved state.

### Example API Families

#### Customers

1. `GET /api/customers`
2. `POST /api/customers`
3. `PUT /api/customers/{id}`
4. `GET /api/customers/{id}/summary`

#### Projects

1. `GET /api/projects`
2. `POST /api/projects`
3. `PUT /api/projects/{id}`
4. `GET /api/projects/{id}/rates`

#### Time

1. `GET /api/time-entries`
2. `POST /api/time-entries`
3. `PUT /api/time-entries/{id}`
4. `DELETE /api/time-entries/{id}` if deletes are supported

#### Expenses

1. `GET /api/expenses`
2. `POST /api/expenses`
3. `PUT /api/expenses/{id}`
4. `DELETE /api/expenses/{id}` if deletes are supported

#### Invoices

1. `GET /api/invoices`
2. `POST /api/invoices`
3. `PUT /api/invoices/{id}`
4. `GET /api/invoices/{id}`
5. `GET /api/invoices/{id}/eligible-items`
6. `POST /api/invoices/{id}/selection`
7. `POST /api/invoices/{id}/issue`
8. `GET /api/invoices/{id}/pdf`

#### Payments

1. `GET /api/payments`
2. `POST /api/payments`
3. `PUT /api/payments/{id}`
4. `GET /api/payments/{id}/applications`
5. `POST /api/payments/{id}/applications`
6. `DELETE /api/payments/{id}/applications/{application_id}` or equivalent update route

## Frontend Architecture

### Rendering Strategy

1. The shared page shell is rendered by the backend.
2. Each major screen has a dedicated JS module.
3. Each screen JS module loads the page dataset and manages local view state.
4. The backend is not responsible for live DOM updates after initial page load.

### Shared Layout Strategy

Candidate file layout:

1. `templates/base.html`
2. `templates/customers.html`
3. `templates/projects.html`
4. `templates/time.html`
5. `templates/expenses.html`
6. `templates/invoices.html`
7. `templates/payments.html`
8. `static/js/customers.js`
9. `static/js/projects.js`
10. `static/js/time.js`
11. `static/js/expenses.js`
12. `static/js/invoices.js`
13. `static/js/payments.js`

### Client-State Rules

1. Keep page-local arrays or store objects in memory only.
2. Do not use IndexedDB as a second datastore.
3. Local filtering is acceptable for screen responsiveness.
4. After a successful save, patch local state or re-fetch the working table.
5. Never let the browser become the financial source of truth.

### Screen Interaction Model

1. Customers, projects, time, expenses, invoices, and payments can load the relevant working table in one request and filter locally.
2. Invoice editing should fetch narrower scoped datasets when needed, such as eligible items for one invoice or project.
3. Payment application should fetch the selected payment plus open invoices for the relevant customer.

## Security Architecture

### Trust Model

1. v1 is a trusted local-user application with no login.
2. Security focus is data integrity and accidental loss prevention, not multi-user access control.

### Data Protection

1. The database file should live in an application-controlled local folder.
2. Backup and restore should be explicit actions.
3. OneDrive or similar sync should be treated as backup and transport, not live concurrent access.
4. The application should be closed before sync-sensitive file movement.

### Input And Integrity Controls

1. Unique constraints must protect invoice numbers and project numbers.
2. Foreign keys must be enabled.
3. Payment application limits must be enforced server-side.
4. Invoice linking and unlinking must run inside transactions.

## Error Handling Strategy

1. Server validation errors return structured JSON with field-level detail where possible.
2. Transaction failures roll back completely.
3. PDF generation failures do not leave partial invoice state without clear status.
4. File backup and restore operations must fail clearly and preserve the current file unless confirmed.
5. UI notifications should distinguish validation issues from system errors.

## Testing Strategy

### Automated Testing Priorities

1. Database schema and constraints.
2. Invoice selection and deselection behavior.
3. Invoice total calculations.
4. Payment application and over-application prevention.
5. Customer balance derivation.

### Test Levels

1. Unit tests for bookkeeping calculations and service functions.
2. Integration tests for database transactions and API endpoints.
3. Light end-to-end tests for critical flows.

Critical flows:

1. Create time and expense.
2. Issue invoice.
3. Record payment.
4. Apply payment.

## Deployment And Runtime Model

1. v1 runs as a local FastAPI app accessed through the local browser.
2. Packaging can remain simple in early development.
3. Desktop shell packaging can remain a later option if desired, but is not required for the architecture.

## Observability

1. Structured application logging to a local log file.
2. Audit-like timestamps on major entities.
3. An optional integrity-check screen or command for database validation.

## Implementation Roadmap

### Phase 1: Skeleton And Data Layer

1. Create project structure for FastAPI, templates, static assets, and the database module.
2. Define schema and initialize the SQLite database.
3. Implement connection management, transactions, and basic integrity checks.
4. Seed or manually enter sample customer and project data.

### Phase 2: Core Master Data Screens

1. Build the shared shell and navigation.
2. Build the customers screen and modal.
3. Build the projects screen and modal.
4. Implement project rate management.

### Phase 3: Source Entry Screens

1. Build the time entry screen and modal.
2. Build the expenses screen and modal.
3. Add local filtering and live table updates.
4. Expose invoice linkage status in both ledgers.

### Phase 4: Invoice Workflow

1. Build the invoice ledger.
2. Build the invoice editor using eligible time and expense selection.
3. Generate the server-side invoice PDF.
4. Support edit and reissue flow.

### Phase 5: Payments Workflow

1. Build the payments ledger.
2. Build the payment entry flow.
3. Build the payment application flow across open invoices.
4. Surface customer balances and unapplied credit.

### Phase 6: Operations And Hardening

1. Add backup and restore.
2. Add XLSX audit export.
3. Add integrity-check utilities.
4. Expand automated test coverage on bookkeeping rules.

## Risks And Mitigations

### Risk 1: Docs Drift From Actual User Decisions

Likelihood: Medium.

Impact: High.

Mitigation: Treat user decisions as highest-priority input and keep the plan and PRD synchronized as implementation proceeds.

### Risk 2: Spreadsheet Habits Leak Into The Data Model

Likelihood: Medium.

Impact: Medium.

Mitigation: Keep spreadsheet export as an output only, never as the editable system of record.

### Risk 3: Frontend JS Grows Ad Hoc Without Structure

Likelihood: Medium.

Impact: Medium.

Mitigation: Use one JS module per screen, shared utility helpers, and a consistent page-store pattern.

### Risk 4: Financial Truth Is Accidentally Calculated Differently In JS And Python

Likelihood: Medium.

Impact: High.

Mitigation: Keep authoritative calculations on the backend and let JS compute only view convenience values.

### Risk 5: SQLite File Is Synced While Open

Likelihood: Low to Medium.

Impact: Medium.

Mitigation: Document the single-active-machine rule and encourage backups or sync only while the app is closed.

### Risk 6: PDF Generation Adds Hidden Complexity

Likelihood: Medium.

Impact: Medium.

Mitigation: Reuse the invoice HTML template structure and choose a simple, stable HTML-to-PDF path early.

## Alignment Notes And Remaining Open Question

1. Customer balance remains a derived value and should not be stored as a cached customer-table column.
2. Time and expense rows keep cached `customer_id` values in v1 to simplify filtering and reporting.
3. Customers and projects stay available for history in v1, so they do not carry separate active or inactive lifecycle flags.
4. Invoice due date is derived from `invoice_date + terms_days` rather than stored as an independent field.
5. Recommendation for server-side invoice PDF generation: start with WeasyPrint if the local packaging footprint is acceptable.
6. Backup and restore should be exposed in the UI, not as CLI utilities.
7. Spreadsheet import remains out of scope for v1.

## Recommended Immediate Next Steps

1. Create the minimal FastAPI bootstrap around the SQLite database and startup migration runner.
2. Build the first repository-style data access helpers for customers, projects, time, and expenses.
3. Add the first screen-specific endpoints using the existing API contract plan as the source.
4. Choose the PDF generation library before invoice PDF work begins.
