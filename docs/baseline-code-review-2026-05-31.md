# Winds Ledger Baseline Code Review

## Summary

The baseline issues identified in the original review have been remediated in the current tree. Current open finding count for the reviewed scope: 0. Validation after the cleanup pass: 26 backend API tests passed, including new regressions for issued-invoice immutability, ISO date validation, clearer project customer errors, and deterministic clock handling.

## Critical Issues (Security, Correctness, Performance)

  - **[Blocker]** Historical baseline finding: issued invoice amounts could still change after issuance by editing linked time or expense rows.
    - Evidence: runtime probe against a temp database changed invoice `201` from `67275` cents to `87975` cents by sending `PUT /api/time-entries/403`; the API returned `200` and the updated time row still referenced `INV-2026-014`.
    - Resolution: the update paths now reject edits for rows linked to issued invoices in [backend/app/time_entries.py](backend/app/time_entries.py#L422) and [backend/app/expenses.py](backend/app/expenses.py#L353). Regression coverage was added in [backend/tests/test_time_api.py](backend/tests/test_time_api.py#L124) and [backend/tests/test_expenses_api.py](backend/tests/test_expenses_api.py#L142).

  - **[Major]** Historical baseline finding: time, expense, and payment write models accepted arbitrary date strings even though downstream code assumed ISO dates.
    - Evidence: runtime probe created a payment with `payment_date="not-a-date"`, a time entry with `entry_date="also-not-a-date"`, and an expense with `entry_date="bad-date"`; all three endpoints returned `200` and persisted the invalid values.
    - Resolution: shared ISO date validation now lives in [backend/app/date_utils.py](backend/app/date_utils.py#L15) and is enforced by [backend/app/time_entries.py](backend/app/time_entries.py#L144), [backend/app/expenses.py](backend/app/expenses.py#L132), and [backend/app/payments.py](backend/app/payments.py#L155). Regression coverage was added in [backend/tests/test_time_api.py](backend/tests/test_time_api.py#L109), [backend/tests/test_expenses_api.py](backend/tests/test_expenses_api.py#L124), and [backend/tests/test_payments_api.py](backend/tests/test_payments_api.py#L133).

## Logic & Edge Cases

  - **[Major]** Historical baseline finding: project create/update reported the wrong error for invalid customer IDs and any other database integrity failure.
    - Evidence: runtime probe posting a project with `customer_id=999999` returned `409` with `{"detail":"Project number must be unique."}`.
    - Resolution: project writes now require a positive customer id in [backend/app/projects.py](backend/app/projects.py#L136), resolve customer existence before insert/update in [backend/app/projects.py](backend/app/projects.py#L292), [backend/app/projects.py](backend/app/projects.py#L334), and [backend/app/projects.py](backend/app/projects.py#L374), and map remaining SQLite constraint failures more accurately in [backend/app/main.py](backend/app/main.py#L38), [backend/app/main.py](backend/app/main.py#L219), and [backend/app/main.py](backend/app/main.py#L235). Regression coverage was added in [backend/tests/test_projects_api.py](backend/tests/test_projects_api.py#L127).

## Simplification & Minimalism

  - **[Minor]** Historical baseline finding: `invoice_summary()` was dead code that duplicated summary logic already built in `invoice_editor_payload()`.
    - Evidence: the baseline pass found that `invoice_summary()` had no call sites while invoice editor responses were already assembling a parallel summary.
    - Resolution: the unused helper was removed; the active summary path now lives only in [backend/app/invoices.py](backend/app/invoices.py#L592).

## Elegance & Idiomatic Enhancements

  - **[Nit]** Historical baseline finding: common time/date helpers were duplicated across modules, which invited drift over time.
    - Evidence: `utc_now()` was redefined in multiple modules and `derive_due_date()` existed in both invoice and payment code.
    - Resolution: shared date helpers now live in [backend/app/date_utils.py](backend/app/date_utils.py#L7), [backend/app/date_utils.py](backend/app/date_utils.py#L34), and [backend/app/date_utils.py](backend/app/date_utils.py#L38), with active callers updated across the reviewed scope.

## Documentation & Testability

  - **[Minor]** Historical baseline finding: the regression suite was time-sensitive and would start failing as soon as the calendar moved past the seeded due dates.
    - Evidence: the baseline pass relied on seeded invoice due dates and hard-coded status assertions in [backend/tests/test_invoices_api.py](backend/tests/test_invoices_api.py), which would eventually drift out of sync with `date.today()`.
    - Resolution: status/report code now reads a shared overridable current date via [backend/app/date_utils.py](backend/app/date_utils.py#L34), [backend/app/invoices.py](backend/app/invoices.py#L509), [backend/app/payments.py](backend/app/payments.py#L213), and [backend/app/reporting.py](backend/app/reporting.py#L192). The API tests now pin that value in their temp environments, for example in [backend/tests/test_invoices_api.py](backend/tests/test_invoices_api.py) and [backend/tests/test_reporting_api.py](backend/tests/test_reporting_api.py).

## Positive Observations

  - The app bootstrap is easy to reason about: settings, migrations, seed data, and route registration are all centralized in [backend/app/main.py](backend/app/main.py).
  - The test harness uses isolated temp databases per test case, which keeps the current suite fast and reproducible enough for local iteration.
  - The reporting/export slice does a real XLSX container round-trip in [backend/tests/test_reporting_api.py](backend/tests/test_reporting_api.py#L59), which is better than asserting only HTTP headers.
  - The cleanup pass added focused regression coverage for every baseline defect that was fixed, which materially improves confidence in future work.
  - Twenty-six backend API tests passed after remediation, including the newly added guards and deterministic date coverage.
  - For a prototype ledger, it is still irritatingly serviceable; at least the accounting facts have mostly stopped wandering off after finalization.

## Prioritized Findings Summary

| # | Severity | Section | Finding | Effort | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | **Blocker** | Critical Issues | Issued invoices could be mutated indirectly through billed time/expense edits | Med | Resolved |
| 2 | **Major** | Critical Issues | Date fields accepted arbitrary strings across payment, time, and expense writes | Med | Resolved |
| 3 | **Major** | Logic & Edge Cases | Project create/update misreported foreign-key failures as duplicate project numbers | Low | Resolved |
| 4 | **Minor** | Simplification & Minimalism | Unused `invoice_summary()` duplicated active summary logic | Low | Resolved |
| 5 | **Minor** | Documentation & Testability | Clock-dependent status tests would drift and fail over time | Low | Resolved |
| 6 | **Nit** | Elegance & Idiomatic Enhancements | Duplicate helper functions increased maintenance drift risk | Low | Resolved |
