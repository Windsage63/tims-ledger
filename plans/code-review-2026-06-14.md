# Tim's Ledger Code Review - 2026-06-14

## Summary

The application is coherent and compact, with a clear FastAPI/domain-module split and a mostly consistent vanilla JavaScript screen pattern. After review follow-up, the remaining main concerns are practical: persistent user/database text is still rendered through `innerHTML` on most screens, and payment saving is split across multiple committed requests even though payment fields and applications are one accounting operation.

Open finding count: 0 Blocker, 2 Major, 1 Minor, 0 Nit.

## Critical Issues (Security, Correctness, Performance)

  - **Major** User-controlled ledger text is inserted into generated HTML without escaping across most frontend screens.
    - Evidence:
      - `frontend/js/app.js:214` builds AR rows with `setHtml(...)`; `frontend/js/app.js:221-222` interpolates `customer.customer_name`, `customer.contact_name`, and `customer.email` directly.
      - `frontend/js/customers.js:201-217` renders customer names, contact names, email, phone, city, and state into `list.innerHTML` without `escapeHtml`.
      - `frontend/js/projects.js:143-148` and `frontend/js/projects.js:213-216` render customer/project text into option and table HTML without escaping.
      - `frontend/js/time.js:152-154` and `frontend/js/time.js:236-239` render project/customer/description text without escaping.
      - `frontend/js/expenses.js:141-164` and `frontend/js/expenses.js:222-225` render project, customer, category, vendor, and description fields without escaping.
      - `frontend/js/payments.js:256-258` and `frontend/js/payments.js:326-328` render customer and payment reference text without escaping.
      - By contrast, `frontend/js/invoices.js:293-298` and `frontend/js/company.js:57-63` already use `escapeHtml`, so the safer pattern exists locally.
    - Risk: a customer/project/time/expense/payment field containing markup can execute script in the local app context. Because the page can call local API routes, this is more than cosmetic.
    - Suggested improvement: standardize on escaping before every template interpolation sourced from users or the database. For rows/options, use `escapeHtml(...)` consistently or switch simple cells/options to DOM creation and `textContent`.

  - **Major** Payment save is not atomic across payment fields and invoice applications.
    - Evidence:
      - Product requirement: `docs/tims_ledger_prd.md:231` says "Save Payment must persist both payment fields and invoice applications."
      - `frontend/js/payments.js:536-568` saves applications separately from the payment. For an existing payment with the same customer, it calls `saveApplicationsForPayment(payment.id)` before the `PUT`; after the `POST`/`PUT`, it calls `saveApplicationsForPayment(data.payment.id)` again.
      - `backend/app/payments.py:263` commits `create_payment`, `backend/app/payments.py:303` commits `update_payment`, and `backend/app/payments.py:374` separately commits `replace_payment_applications`.
    - Risk: if step two fails after step one succeeds, the ledger can persist a payment without the intended applications, or persist application changes even when the payment field update fails. That breaks the "one source of truth" expectation for balances.
    - Suggested improvement: add a single backend save endpoint that accepts payment fields plus applications and commits once. Internally use no-commit helpers for create/update/application replacement, mirroring the invoice `save_print_invoice` transaction pattern.

## Logic & Edge Cases

  - **Minor** Discarding a new invoice clears state but leaves stale editor fields on screen when there is no saved invoice to reload.
    - Evidence: `frontend/js/invoices.js:540-558` sets `invoicesState.editor.invoice = null` and calls `render()`; `frontend/js/invoices.js:346-349` immediately returns when `invoice` is falsy, so the old form values are not cleared.
    - Risk: after "Discard New", a user can still see the discarded invoice form values, which makes the UI look like the draft still exists.
    - Suggested improvement: add a `renderEmptyEditor()` path that clears form controls, summary values, source lists, and disables Save/Print when no invoice is selected.

## Accepted Follow-Up Completed

  - New time, expense, invoice, and payment drafts now default to the browser's current local date.
  - Backup creation now has a five-second cooldown in the overview UI.
  - The unused project draft ID helper was removed.
  - The overview page now uses the shared nav-state helper.
  - Stale roadmap cards were removed from workflow screens.
  - The alternate static screen route and related user-facing copy were removed; `/frontend/html/...` is the remaining screen route family.
  - The deleted frontend tests are treated as an intentional project decision and are no longer listed as a finding.

## Positive Observations

  - The backend domain modules are easy to follow: Pydantic write models sit near their persistence helpers, and routes consistently wrap response data in `response_envelope`.
  - Invoice save/print is a good model for multi-step accounting work: create/update, source-row replacement, HTML generation, and final commit are coordinated in one flow.
  - Backup and restore use a safety backup and archive path checks, which is exactly the right instinct for local production data.
  - The codebase is refreshingly small, which means every mess is still small enough to be blamed on a specific line instead of a committee.

## Prioritized Findings Summary

| # | Severity | Section | Finding | Effort |
| --- | --- | --- | --- | --- |
| 1 | **Major** | Critical Issues | User/database text is inserted into generated HTML without escaping across most frontend screens | Med |
| 2 | **Major** | Critical Issues | Payment fields and applications save in separate committed operations | Med |
| 3 | **Minor** | Logic & Edge Cases | Discarding a new invoice can leave stale editor fields visible | Low |
