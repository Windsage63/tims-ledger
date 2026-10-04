# Phase 1 Plan — Declutter, Menu Grouping, Bug Fixes

Decisions carried in from your answers:

  - **Home**: the statement stays until the Customer Center exists (Phase 3). **Backup/Restore and the XLSX export move to Settings now**, and a **Back up** button + "last backup" indicator is added to the top bar of every page.
  - **Due dates**: the backend already stores `terms_days` and prints the due date on invoices; only the UI hard-codes Net 30. Phase 1 adds a **Terms** select (Due on receipt / Net 10 / 15 / 30 / 45 / 60), a **Due** column, and an **Overdue** badge. The AR aging report stays in Phase 3.
  - **Save/Print** stays as one action.
  - **No payment method** field.

## 1. Shell & navigation

| File | Change |
| --- | --- |
| `backend/app/pages.py` | Add `group`, `heading`, `help_text`, `new_label` and drop the sidebar status fields. Reorder the registry to **Home · Sales (Invoices, Receive Payments, Customers) · Work (Projects, Time, Expenses) · Settings**. Filenames and routes are unchanged. |
| `frontend/templates/base.html` | Flat dark sidebar with group headings, no status card. New **top bar**: page title, `?` help popover (old sidebar help text), page actions, **+ New** menu, **Back up** button + last-backup chip. Neutral, dense theme tokens. Shared component classes (`card`, `btn-*`, `field`, `data-table`, `badge`, `tab`, `kpi`). Defines the missing `danger`, `warn` and `calm` colors. |
| `frontend/js/shell.js` (new) | Menus (click-away / Esc), global Back up action, last-backup chip, `backups:changed` event. |
| `frontend/js/utils.js` | `showToast()`, `syncFilterButtons()`, `consumeNewRecordRequest()` (the `#new` deep link used by **+ New**), and invoice terms/overdue helpers. |

## 2. Screens

All screens: remove the hero banner and explanatory headings, use one compact KPI strip, filters on a single toolbar row, segmented status tabs, and tighter table rows.

  - **Home**: KPIs Open A/R · Unapplied Credit · Net Receivables · Unbilled Work, plus the A/R table and statement. Customer/Project counts and backup controls are removed.
  - **Customers**: the card grid becomes a **table** (Name/Contact, Phone, Email, City, Open A/R, Status).
  - **Invoices**: status labels corrected (unprinted = **Draft**, printed and unpaid = **Open**, plus **Overdue** and **Paid**). Adds Due and Balance columns and the Terms select. KPIs become Open Balance · Overdue · Draft Total.
  - **Receive Payments**: the "Visible Payments" count is removed and deleting a saved payment now asks for confirmation.
  - **Settings** (formerly Company): Company profile and preview, **Backup & Restore**, **Audit Export (XLSX)**.

## 3. Bug fixes

  - `danger`/`warn`/`calm` colors were never defined, so status badges and delete buttons were unstyled.
  - Invoice status labels were wrong: unprinted invoices were shown as "Open".
  - Customer, project, expense, payment and A/R rows inserted names without `escapeHtml`. This breaks the AGENTS.md rule.
  - `window.alert` is replaced with non-blocking toasts.
  - Typos: "Non-GAP" and "it's".
  - Deleting a payment didn't ask for confirmation.

## 4. Docs

`AGENTS.md`, `README.md`, `docs/tims_ledger_prd.md`, and `docs/workflows.md` will be updated for the nav groups, Settings (backup/export location), the top-bar backup, and invoice terms. There are no API changes.

## 5. Deferred

  - Vendoring Tailwind/fonts for offline use. It needs a build step, so it's a separate decision.
  - Keyboard shortcuts and the unsaved-changes guard (Phase 2).

## 6. Verification

  - `py_compile` on the backend.
  - Run `startup.bat` and load every page.
  - Check the browser console for errors.
  - Exercise: + New on each screen, Back up, restore list rendering, invoice terms/due/overdue, and the filters.
