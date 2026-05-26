# Windsage Ledger Roadmap

## Current Direction

The backend now covers the core local-first accounting workflows. The next work should make those workflows usable from the React app, then add document output and deeper migration tooling.

## Phase A: Frontend Foundation

  - [x] Replace the placeholder screen with a real app shell and navigation.
  - [x] Add a typed API client.
  - [x] Show backend health and local workflow status.
  - [x] Add first dashboard summaries for the proof workflow.

## Phase B: Frontend CRUD Workflows

  - [x] Build first customer and project screens.
  - [x] Build first time entry and expense screens.
  - [x] Add expense category management.
  - Customer, project, time, and expense screens currently cover first create/list flows; deeper edit/filter workflows are still open.
  - Preserve dense, work-focused layouts suitable for repeated accounting work.

## Phase C: Invoice Workflow UI

  - [x] Add backend invoice candidate selection.
  - [x] Add backend draft invoice creation from selected time and expenses.
  - [x] Add backend invoice register/detail and send/finalize endpoints.
  - [ ] Build invoice candidate selection UI.
  - [ ] Build invoice register and invoice detail screens.
  - [ ] Wire send/finalize actions into the React app.

## Phase D: Payments and Balances UI

  - [x] Add backend payment and advance recording.
  - [x] Add backend payment application workflow.
  - [x] Add backend customer balances and unapplied credit calculations.
  - [x] Add backend AR aging and open invoice CSV exports.
  - [ ] Build payment entry and application screens.
  - [ ] Build customer balance and report screens in React.

## Phase E: Documents and Invoice 662

  - [ ] Add invoice PDF rendering.
  - [ ] Match the existing invoice 662 style closely enough for real validation.
  - [ ] Store generated invoice files as managed outputs.

## Phase F: Import and OCR UX

  - [x] Add backend workbook preview.
  - [x] Add backend receipt OCR review and approval flow.
  - [ ] Add workbook preview and reconciliation screens.
  - [ ] Add import staging and discrepancy reports.
  - [ ] Add receipt OCR review queue in React.

## Phase G: Hardening and Packaging

  - [x] Add backup creation.
  - [ ] Add restore flow.
  - [ ] Add launcher/packaging plan.
  - [ ] Add optional local PIN/password protection.
  - [ ] Create release checklist for first real bookkeeping trial.
