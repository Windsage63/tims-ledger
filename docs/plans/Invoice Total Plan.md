# Invoice Total Plan

Date: November 8, 2026

Status: Implemented on November 8, 2026. Automated and isolated browser verification passed. The normal application backend was restarted with the updated code after stale duplicate instances were identified. Native print-preview verification remains limited as noted below.

Each printed invoice will show the charges for that invoice under **Total Invoice**. Customer account balances and statements remain on Customers. Invoice totals will be independent of other invoices, payments, and unapplied credits.

## 1 Required behavior

| Area | Change |
| --- | --- |
| Printed invoice summary | Replace `Sub-Total Invoice` with `Total Invoice`. Remove `Prior Balance`, `Unapplied Credit`, and `Total Due`. |
| Invoice editor summary | Keep Time Total and Expense Total. Rename Invoice Total to Total Invoice. Remove Prior Balance, Unapplied Credit, and Open Balance After Print. |
| Invoice editor header | Use Total Invoice for the charges. Retain the existing Open Balance, which belongs to the selected invoice. |
| Customer balances and statements | Keep the existing displays and calculations. |
| Payments and invoice status | Keep payment applications, invoice open balances, and Draft, Open, Overdue, and Paid behavior. |

For invoice 682, the printed summary will contain one emphasized row:

| Summary | Amount |
| --- | ---: |
| **Total Invoice** | **$750.00** |

That figure is the sum of its selected time and expense charges. It remains $750 whether the invoice is unpaid, partially paid, or fully paid. Do not add replacement payment, credit, or amount-due rows to the printed invoice.

Keep the existing Services and Expenses section subtotals, invoice date, due date, terms, notes, company details, and project reference format.

## 2 Backend changes

In `backend/app/invoices.py`:

1. Update `build_invoice_print_html` to render only the Total Invoice row in the final summary table, using `summary.invoice_total_cents`.
2. Remove the three account-summary rows and their unused string-format arguments. Preserve the existing emphasis on the final total row and check its spacing with the reduced table.
3. In both `invoice_editor_payload` and `invoice_new_editor_payload`, reduce the editor `summary` to `time_total_cents`, `expense_total_cents`, and `invoice_total_cents`. Remove `prior_balance_cents`, `unapplied_credit_cents`, and `open_balance_after_issue_cents` from that summary and remove the combined account-balance calculation.
4. Preserve the invoice object's `invoice_amount_cents`, `paid_amount_cents`, and `open_balance_cents` for the ledger, payment workflow, and invoice status.

Preserve the top-level invoice object's existing `prior_balance_cents` and `unapplied_credit_cents` fields, the query that supplies them, and the `prior_balance_cents` helper. The XLSX OpenInvoices audit sheet consumes these fields through `backend/app/reporting.py`. This change removes their use in invoice presentation and editor summary calculations without changing that export contract.

No database migration, new endpoint, or change to Save/Print request bodies is required. The editor summary response changes as described above; the remaining invoice response fields stay available.

## 3 Frontend changes

In `frontend/templates/invoices.html`:

1. Remove the three account figures and their elements: `invoice-summary-prior-balance`, `invoice-summary-credit`, and `invoice-summary-open-after-issue`.
2. Change the editor header and summary labels to Total Invoice. Keep the existing total value element IDs.
3. Arrange the remaining summary as Time Total, Expense Total, and Total Invoice, preserving the dense desktop layout and readable wrapping at narrower widths.

In `frontend/js/invoices.js`:

1. Remove prior-balance and unapplied-credit inputs from `recalculateEditorSummary`. Build the summary from the three charge totals only, without retaining obsolete account-summary keys through the existing object spread.
2. Remove the three corresponding updates from `updateEditorSummary`.
3. Keep the selected invoice's open-balance calculation as its charges minus payments applied to that invoice. Continue displaying that value in the existing Open Balance field.
4. Preserve browser-local source selection, detached drafts, Edit Mode checks, discard warnings, save behavior, and protected printing.

## 4 Existing saved documents

The template change applies when Save/Print generates a document. Existing saved HTML files, including `app-data/invoices/invoice-19-682.html`, retain their current contents until deliberately regenerated.

Keep protected Print Saved Invoice as a read-only document GET. Do not rewrite saved files during startup, document retrieval, ordinary printing, or payment entry.

For a selected existing invoice that needs the new layout, take an application backup, review its saved fields and selected source rows, enable Edit Mode, and use the existing Save/Print action without changing those fields or selections. Regeneration uses the current invoice data and Company profile, as it does today. Do not add automatic or bulk regeneration to this change.

## 5 Documentation updates

Update the current reference documents in the implementation change:

| Document | Update |
| --- | --- |
| `docs/workflows.md` | Replace the invoice workflow guidance about displaying prior customer balances with the Total Invoice rule. Describe the treatment of existing saved documents. |
| `docs/tims_ledger_prd.md` | Specify that printed invoice totals contain only that invoice's source charges; account balances and statements belong on Customers. |
| `docs/API Reference.md` | Document the three-field editor summary, the generated document's single total row, and the continued read-only behavior of the document GET. |

Preserve completed historical plans. Record implementation and verification results at the end of this plan when the work is complete.

## 6 Verification

Use disposable in-memory databases for backend checks and an isolated data directory for manual Save/Print checks. Start the app through `startup.bat` with `TIMS_LEDGER_DATA_DIR` and `TIMS_LEDGER_DB_PATH` pointing to that directory and a separate port. Confirm the active paths through system status before creating or changing fixtures. Do not test saves against `app-data/tims-ledger.db`.

Add focused backend regression coverage in `tests/test_invoice_totals.py` for the following behavior:

- A $750 invoice prints Total Invoice of $750 when the customer has several other outstanding invoices and substantial unapplied credit. The removed summary rows are absent.
- Partial and full payment applications change that invoice's open balance without changing its printed charge total.
- New and saved editor summaries contain the three charge totals. Customer statement balances and the existing OpenInvoices audit columns still agree with the saved records.

Extend the existing frontend checks only where needed to verify that source selection recalculates charge totals, retains the invoice's own open balance, and leaves saved browse records detached. Retain the existing regression checks for protected printing and Edit Mode.

Run the repository checks in the checked-in venv:

```powershell
if ($env:VIRTUAL_ENV) { $env:VIRTUAL_ENV } else { . .\.venv\Scripts\Activate.ps1 }
python -m py_compile (Get-ChildItem backend\app -Filter *.py | ForEach-Object { $_.FullName })
python -m unittest discover -s tests -p "test_*.py"
node --test tests/frontend-phase2.test.cjs
```

Manually verify the invoice editor, generated document, and browser print preview. Include a services-only invoice, a mixed services-and-expenses invoice, and a zero-dollar invoice containing selected source rows. Confirm the single final total is readable, section subtotals and fractional-cent expense results are preserved, and empty invoices are still rejected.

On an isolated existing invoice, verify that Edit Mode plus Save/Print generates the new layout while retaining the intended fields and source links. Compare the saved database contents and document hash before and after protected printing to confirm that reprinting performs no writes. Verify Customers still shows its balances and statement detail.

## 7 Completion criteria

- Newly generated invoice documents contain Total Invoice as their only final summary row.
- Other invoices, applied payments, and unapplied credit cannot alter that charge total.
- The invoice editor shows the three charge totals and retains its separate invoice-specific Open Balance.
- Customer balances, statements, payment applications, invoice statuses, and audit export behavior are preserved.
- Existing saved documents change only through deliberate Save/Print regeneration.
- Documentation and verification results accompany the implementation.

## 8 Implementation and verification results

Implemented the printed Total Invoice row, the three-field backend/editor summary, the matching editor labels, and the reference documentation updates. Customer balance calculations, invoice-specific open balances, payment applications, and the existing audit export fields are preserved. No database migration was needed.

- All 15 backend tests passed, including new coverage for other invoices, substantial unapplied credit, partial/full payment, customer statements, and audit export values. Python compilation passed.
- All 15 frontend regression checks passed, including source-selection totals, detached browse records, Edit Mode, and protected saved-document printing. The invoice controller syntax check passed.
- Started the app through `startup.bat` on port 8016 with isolated data under `outputs/invoice-total-verification-20261108`. Verified the configured database path before fixture writes. Fixtures covered services-only ($750), mixed services and fractional-cent mileage ($154.73), and zero-dollar invoices; empty invoices were rejected.
- Browser checks confirmed the simplified editor and generated mixed invoice. Edit Mode plus Save/Print regenerated the document and relocked the editor without changing invoice fields, source links, or payments. Protected reprinting preserved the complete database dump and all saved invoice file hashes. Customers continued to show Open A/R, Unapplied Credit, Net Balance, and statement details.
- Inspected the generated document layout and retained `outputs/invoice-total-verification-20261108/invoice-preview.png`. The in-app browser could not capture the native print dialog. The Firefox fallback was stopped by Computer Use because URL policy enforcement is unsupported for that Windows browser; native print preview was not verified.
- Follow-up runtime inspection found two backend instances listening on port 8004, with old Python code still serving requests. Stopped the stale instances and the isolated test server, leaving one freshly started backend on port 8004. Confirmed its editor response has exactly the three charge summary fields. Read-only fingerprints confirmed production database records and saved invoice documents were unchanged by the restart.

Existing saved documents keep their previous layout until deliberately regenerated through Edit Mode and Save/Print. Deleting those files is unnecessary. PDFs exported through the browser are separate copies and must be saved again after regeneration.
