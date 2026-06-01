### Summary

The HTML-first invoice print flow is a workable direction and the user-input escaping is handled correctly, but three production-impacting issues remain in the current implementation. Total findings: 3 Major, 1 Minor.

### Critical Issues (Security, Correctness, Performance)

- **[Major]** Issued invoices are no longer immutable because the printable document is rebuilt from live customer data on every request.
Evidence: [backend/app/invoices.py](c:\SDai\SDai\windsage-ledger\backend\app\invoices.py#L591) joins current `customers` fields into the invoice payload, [backend/app/invoices.py](c:\SDai\SDai\windsage-ledger\backend\app\invoices.py#L658) copies those fields into `invoice`, and [backend/app/invoices.py](c:\SDai\SDai\windsage-ledger\backend\app\invoices.py#L987) regenerates the print document from `invoice_editor_payload()` on demand. That means changing a customer address, phone, or email after issue will change the appearance of historical invoices.
Suggested improvement: persist a print snapshot at issue time, or persist the bill-to and sender fields on the invoice record so issued invoices render from immutable invoice-owned data instead of current customer state.

- **[Major]** The sender/business identity is hardcoded into the renderer, so every environment prints the same company header regardless of actual business settings.
Evidence: [backend/app/invoices.py](c:\SDai\SDai\windsage-ledger\backend\app\invoices.py#L417), [backend/app/invoices.py](c:\SDai\SDai\windsage-ledger\backend\app\invoices.py#L418), [backend/app/invoices.py](c:\SDai\SDai\windsage-ledger\backend\app\invoices.py#L419), and [backend/app/invoices.py](c:\SDai\SDai\windsage-ledger\backend\app\invoices.py#L468) embed one specific company name, address, email, phone, and remittance text directly in code.
Suggested improvement: move sender header and footer fields into configuration or a business-profile record and render them through the same Python string interpolation path.

- **[Major]** The legacy PDF path is still publicly exposed and writes separate invoice output that no longer matches the primary HTML print representation.
Evidence: [backend/app/main.py](c:\SDai\SDai\windsage-ledger\backend\app\main.py#L307) still serves `/api/invoices/{invoice_id}/pdf`, while [backend/app/invoices.py](c:\SDai\SDai\windsage-ledger\backend\app\invoices.py#L971) and [backend/app/invoices.py](c:\SDai\SDai\windsage-ledger\backend\app\invoices.py#L973) still stamp `pdf_file_name` during issue. The UI now opens `/print`, so the product has two divergent invoice renderers with different outputs and different test coverage.
Suggested improvement: either retire `/pdf` and the `pdf_file_name` side effect now, or make `/pdf` explicitly derive from the same printable source so both representations stay consistent.

### Logic & Edge Cases

- **[Minor]** The new print route only has a happy-path test, so access-control and regression behavior for draft or missing invoices is currently unverified.
Evidence: [backend/tests/test_invoices_api.py](c:\SDai\SDai\windsage-ledger\backend\tests\test_invoices_api.py#L98) through [backend/tests/test_invoices_api.py](c:\SDai\SDai\windsage-ledger\backend\tests\test_invoices_api.py#L103) cover successful issued-invoice rendering, but there is no test for 404 on unknown IDs or 422 for draft invoices even though [backend/app/invoices.py](c:\SDai\SDai\windsage-ledger\backend\app\invoices.py#L992) rejects unissued invoices.
Suggested improvement: add focused tests for draft `/print` requests and missing invoice IDs so future refactors do not accidentally expose drafts or change error semantics.

### Simplification & Minimalism

No additional cleanup finding beyond the live `/pdf` compatibility path above. Most remaining complexity is a direct result of supporting both renderers at once.

### Elegance & Idiomatic Enhancements

No additional finding. The direct HTML-string approach is consistent with the stated implementation constraint, and user fields are escaped before interpolation.

### Documentation & Testability

No additional finding beyond the missing error-path coverage above.

### Positive Observations

- The new print entry point is wired end-to-end: backend route, issue response payload, UI link, and regression test all agree on `/api/invoices/{id}/print`.
- User-controlled invoice content is escaped before being inserted into the HTML document, which avoids the obvious injection mistake in this style of renderer.
- The validation order was solid: the invoice slice passed first, then a broader startup plus invoice run confirmed the route integration.
- The codebase remains exactly what you would expect: functional enough to ship, untidy enough to keep billing engineering employed.

### Prioritized Findings Summary

| # | Severity | Section | Finding | Effort |
| --- | --- | --- | --- | --- |
| 1 | **Major** | Critical Issues | Issued invoices render from live customer data instead of immutable invoice data | Med |
| 2 | **Major** | Critical Issues | Sender/company identity is hardcoded into the print renderer | Low |
| 3 | **Major** | Critical Issues | Legacy `/pdf` route and `pdf_file_name` path now diverge from the primary HTML print flow | Med |
| 4 | **Minor** | Logic & Edge Cases | No tests for draft or missing-invoice `/print` behavior | Low |