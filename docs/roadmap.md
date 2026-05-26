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
- [ ] Build time entry and expense screens.
- Add expense category management.
- Preserve dense, work-focused layouts suitable for repeated accounting work.

## Phase C: Invoice Workflow UI

- Build invoice candidate selection.
- Create draft invoices from selected time and expenses.
- Add invoice register and invoice detail.
- Add send/finalize action.

## Phase D: Payments and Balances UI

- Record payments and advances.
- Apply payments to invoices.
- Show customer balances and unapplied credits.
- Show AR aging and open invoice reports.

## Phase E: Documents and Invoice 662

- Add invoice PDF rendering.
- Match the existing invoice 662 style closely enough for real validation.
- Store generated invoice files as managed outputs.

## Phase F: Import and OCR UX

- Add workbook preview and reconciliation screens.
- Add import staging and discrepancy reports.
- Add receipt OCR review queue.

## Phase G: Hardening and Packaging

- Add restore flow.
- Add launcher/packaging plan.
- Add optional local PIN/password protection.
- Create release checklist for first real bookkeeping trial.
