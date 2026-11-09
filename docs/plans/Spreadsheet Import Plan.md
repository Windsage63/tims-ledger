# Spreadsheet Import Plan

Date: November 7, 2026

Status: Implemented and converted on November 7, 2026. The live database and all 26 reconstructed invoice documents passed verification. Fractional-cent expense support is implemented, pre/post-conversion backups are retained, and all temporary conversion tools and rehearsal data have been removed. Payments were not imported; the existing payment record is unchanged. Results follow in section 9.

November 8 correction: The user clarified that time has no billability classification and zero is an ordinary price. All unlinked time is now invoice-eligible regardless of rate. At the user's request, the 32 projects with neither time nor expenses were removed, leaving 17 projects. Customers, time, expenses, invoices, and payments were unchanged by that cleanup. No additional backup was created, as requested. Delete controls were added to Customers, Projects, Invoices, Time, and Expenses; see the current workflows for dependency rules.

Convert Customers, Projects and rates, Time Log, and Expense Log, then reconstruct the real historical invoices from those logs' invoice references and source charges. These four sheets are authoritative. Existing customers, projects, time, and expenses were typed from them and must reconcile to them; existing invoices were created for testing and do not need to be retained.

This is a one-time conversion. All conversion scripts, parsing code, checks, and working files are temporary and must be removed after the conversion is verified. Do not add a permanent importer, application module, API endpoint, upload screen, import tracking tables, or conversion-only changes to the normal CRUD helpers. Retain the source workbook, backups, reviewed mapping, and final reconciliation report as accounting records.

The agreed lasting product change is fractional-cent expense unit-cost support, with matching calculations, editing, and audit export. Use the existing invoice tables and ordinary `invoice_id` links for reconstructed invoices. Do not add a legacy invoice field or permanent conversion tracking tables.

Use Income Tracking, the payments sheet identified by the user, only for invoice dates in column B. Column A may be read solely to match each date to the invoice references in the logs; it does not replace the logs' invoice numbering. All 26 log invoice groups have a unique matching date. Terms are Net 30 for every invoice, as instructed by the user. Do not use other history-page fields for invoice amounts, notes, issue status, payments, balances, validation, or reconciliation. Do not import payments, deposits, opening credits, or payment applications.

## 1 Source inventory

Source: [Timesheet Log and Project Tracking 2026.xlsx](../reference/Timesheet%20Log%20and%20Project%20Tracking%202026.xlsx).

| Sheet | Excel table and full range | Actual source records | Controls and observations |
| --- | --- | ---: | --- |
| Customers | `CustomerList`, `B3:J25` | 7, rows 4 through 10 | Process Barron now has user-entered `na` placeholders in its previously blank fields; all seven rows pass current customer write validation. Fax is blank throughout. |
| Projects | `ProjectsList`, `B3:J61` | 49, rows 5 through 53 | All customer references resolve within Customers. Six projects have positive fixed fees. All ST/OT/TT amounts agree with the app's rate multipliers. |
| Time Log | `TimeLog`, `B3:L285` | 203, rows 5 through 207 | January 12 through November 7, 2026. Quantity total is 1,402; amount is $222,350.00. One row has zero hours. |
| Expense Log | `ExpenseLog`, `B3:L329` | 124, rows 4 through 127 | All source dates are valid Excel dates, spanning January 8 through September 29, 2026. There are now 22 rates of $0.725. Exact quantity-times-rate total is $145,788.845 before rounding. |
| Invoice date lookup | Income Tracking `A4:B29` only | 26 matched dates | A identifies the matching log reference; B supplies the invoice date. All other history-page columns are excluded. |

The time quantity total includes three `HD` units, including two $25,000 bonuses. It should not be presented as 1,402 hours of labor. The expense quantity column mixes miles, days, and individual purchases, so its sum is not a useful reconciliation measure.

Read the named table boundaries and headers, then identify records using their entered fields. Ignore title rows, filtered subtotals, totals rows, and formula-only placeholder rows. In particular, Projects has calculated labels such as `" - "` on otherwise empty rows, and the logs contain formulas far below their last actual record. Partially populated input rows must be reported as errors rather than silently treated as blank.

Customer and project descriptions and time rates in the logs are largely lookup formulas. Read formula text and saved values separately, resolve the customer from the imported project, and independently verify quantity-times-rate calculations. A blank result hidden by `IFERROR` must not become an assumed zero. Preserve the workbook without recalculating or overwriting it.

## 2 Existing data and spreadsheet authority

The inspected `app-data/tims-ledger.db` contains 2 customers, 7 projects, 21 project rates, 42 time entries, 17 expenses, 6 invoices, 1 payment, and 6 payment applications. SQLite quick check passed and foreign key check returned no violations. Reinspect the configured database path and its contents at import time.

### Source records

Treat the existing manually entered records as copies of the source, not a competing source of truth. Reuse their IDs where a counterpart is identified, replace differing entered values with the spreadsheet values, and insert the remaining source records. The report must show the final complete dataset, not only additions.

Map customer 1 to spreadsheet TRK Engineering Services, Inc. and customer 2 to Reinhold Environmental, Inc. Use the spreadsheet names and contact details, correcting the manually entered name/email differences. Map projects 0507, 0518, 0522, 0523, 0524, 0525, and 0526 to spreadsheet 507, 518, 522, 523, 524, 525, and 526. Store project numbers consistently from the spreadsheet as text, without inventing leading zeroes; preserve leading zeroes in actual text identifiers such as ZIP codes. Do not merge different project numbers because their descriptions match.

### Time and expense overlap

Forty-one of the 42 existing time entries match source date, mapped project, description, duration, rate code, rate amount, and line amount. The remaining candidate is database time entry 6, dated February 23, against Time Log row 34, dated February 27. Use the spreadsheet's February 27 date and record the correction; the test invoice does not constrain it.

All 17 existing expenses have identified source counterparts. Descriptions/vendors vary. Expense Log row 26 now contains the valid date March 21, 2026, matching its manually entered counterpart. Database expense 17 still belongs to project 0507, while its corrected source row 11 now belongs to project 524 and invoice 667. Explicitly map and update that existing expense to project 524 rather than inserting a second $41.58 expense. Reconcile each counterpart once, use the spreadsheet's entered values where supplied, and retain useful existing vendor information where the workbook has no equivalent field.

Match financial rows in tiers:

1. The reviewed mapping identifies each source row and its proposed existing target ID, if any.
2. A unique exact business-field match identifies a reuse candidate.
3. A matching financial fingerprint with different descriptions, dates, vendor text, or billing links becomes a review item.
4. Only rows with no exact or plausible existing counterpart become insert candidates.

Use counts of matching occurrences so two legitimate identical entries remain two records. Never deduplicate on date/project/amount alone. Preserve useful record IDs, clear test invoice links, and rebuild real links from the spreadsheet. This also resolves previously unlinked time entries 39 and 42 and expense 17 without introducing a legacy billing field.

### Test invoice cleanup

After a verified application backup, remove the six test invoices, their six payment applications, and their generated test HTML files. Clear their time/expense links in the same conversion transaction before deleting invoice rows. Include this exact cleanup in the dry run. Keep the company profile, migration history, and backups; do not wipe or replace the database.

Leave the existing payment record unchanged. Remove only its applications to the deleted test invoices; the released amount becomes unapplied. Do not create, update, delete, or reapply payments as part of this conversion. List the removal of test invoice applications in the report so it is distinct from importing payment history.

## 3 Field mapping

### Customers

| Source column | Destination |
| --- | --- |
| B Company Name | `customers.customer_name`; use the spreadsheet value for matched and new records |
| C Contact Name | `contact_name` |
| D Address | `street_address` |
| E City | `city` |
| F State | `state` through the existing uppercase normalization; Process Barron's supplied `na` becomes `NA` |
| G ZIP Code | `zip` as text; preserve `01886` and format integral five-digit US ZIP values without `.0` |
| H Phone | `phone` as text |
| I Email | `email` |
| J Fax | Blank in this workbook; no destination field is needed |

Process Barron, row 9, now has user-entered `na` values for street address, city, state, ZIP, and phone. These nonempty placeholders pass the existing `CustomerWrite` rules; preserve them rather than inventing contact information. Only the normal state-uppercase rule changes `na` to `NA`. The missing-field blocker is resolved, so include this customer, project 527, and its two time entries in the full conversion.

### Projects and rates

| Source column | Destination or rule |
| --- | --- |
| B Project No | `projects.project_number` as spreadsheet-derived text through the identity map |
| C Company | Resolve `customer_id` from the customer map |
| D Project Description | `description` for matched and new records |
| E Project_Label | Derived display value; do not import as an independent field |
| F Straight Time | `default_rate_cents`; create built-in ST |
| G Overtime | Validate against ST times 1.5; create built-in OT |
| H Travel Time | Validate against ST times 0.5; create built-in TT |
| I Fixed Fee | Create a custom `HD` rate when positive |
| J Notes | Preserve verbatim in the conversion report and use when reviewing billing intent; do not add a field solely for this conversion |

Positive fixed fees occur on projects 502 ($24,650), 503 ($30,000), 508 ($28,350), 512 ($679.34), 529 ($25,000), and 532 ($25,000). Preserve these as custom rates, including rates that have no corresponding Time Log entry. Do not create extra fee charges merely because a project has a fixed fee.

Project 524 also needs an `HD` rate of zero for its historical placeholder entry. The existing arbitrary custom-rate model supports the `HD` code; no manual invoice lines or separate time billable toggle are needed.

### Time Log

| Source column | Destination or rule |
| --- | --- |
| B Date | `entry_date` as ISO `YYYY-MM-DD`, respecting the workbook date system |
| C Project No | Mapped `project_id`; derive `customer_id` from that project |
| D Customer and E Project Description | Cross-check against Projects; retain original values in the conversion report |
| F Work Description | `description` |
| G Hours | Exact conversion to integer minutes: quantity times 60; for HD, one unit uses 60 minutes |
| H Type | `rate_code`: ST, OT, TT, or custom HD |
| I Spare | Blank throughout this source; ignore |
| J Invoice # | Resolve to the reconstructed real invoice and store its `invoice_id` |
| K Rate | Historical `rate_cents` snapshot; validate against the resolved source rate |
| L Total | Verify against minutes and rate, then store `line_total_cents` |

All current source time rates are representable in cents and all quantities convert to whole minutes. Preserve historical rate snapshots even if a project's future rate changes. The existing create helper obtains the current project rate, so the temporary converter must validate and insert the approved snapshot without adding a permanent import helper to the application.

Time Log row 63 is a zero-hour, zero-dollar annotation for expense-only invoice 670. Preserve it in the conversion report with outcome `annotation_only`; do not invent minutes or weaken the positive-minutes invariant. This leaves 202 actual time records. Keep the two positive-duration, zero-rate rows unless their removal is separately requested. Their zero rates are ordinary prices and do not imply a billability classification.

### Expense Log

| Source column | Destination or rule |
| --- | --- |
| B Date | Validated ISO `entry_date` |
| C Project No | Mapped `project_id`; derive `customer_id` |
| D Customer and E Project Description | Cross-check and preserve in the conversion report |
| F Expense Description | `description`, preserving the full source text |
| G Qty | `quantity`; retain miles/days/units as entered |
| H Type | `category`; all nine observed values are in the permitted category list |
| I Spare | American Express entry/checking flag; ignore for mapping and validation |
| J Invoice # | Resolve to the reconstructed real invoice and store its `invoice_id`; blank remains unlinked |
| K Rate | Exact expense unit cost under the agreed precision change in section 5 |
| L Total | Verified line amount rounded under the approved policy |

There is no separate vendor column. Preserve existing vendor values on reused records. For new records, use an explicit vendor mapping where known, otherwise the documented fallback `Not recorded`. Do not guess a merchant from a generic expense description.

The user confirmed that Spare is used while entering and checking items against the American Express bill and is irrelevant to this import. Its Y/N values must not affect billability, record matching, totals, or import validation. The original workbook preserves those flags; no application field is needed.

Expenses belonging to reconstructed real invoices are billable. Project 535's notes identify its single $5 unlinked expense as a non-billable office expense. Use these source meanings rather than the Spare flag.

## 4 Reconstruct real historical invoices

Rebuild real invoices in the existing `invoices` table by grouping the Time Log and Expense Log on column J, Invoice #. All 203 Time Log source rows and 123 of 124 expense rows have references; the logs identify 26 distinct invoice groups. Link source records through their existing `invoice_id` fields. The unbilled office expense remains unlinked. The conversion left the two zero-price placeholder time rows unlinked, with original references retained in the report; the November 8 correction makes them available for invoice selection like other unlinked time.

| Invoice data | Permitted source and handling |
| --- | --- |
| Invoice number | The Invoice # values in the two logs, normalized as text without `.0`; do not invent prefixes or replace them with the date-lookup keys |
| Invoice date | Income Tracking column B, joined through column A solely to identify the matching log reference; all 26 references have a unique date |
| Project and customer | Projects plus the linked source rows; derive customer from project |
| Services | Time Log rows with the matching invoice reference |
| Expenses | Expense Log rows with the matching invoice reference |
| Invoice total | Sum of the linked source line amounts under the agreed rounding policy |
| Terms | `terms_days = 30` for every invoice, as instructed by the user |
| Issue state | Reconstruct the real historical invoices as issued; preserve their historical invoice day and do not infer Paid status from the history page |
| Invoice notes | Notes supplied by the user, if any; omit absent optional notes and do not read history-page notes |

Use a bounded date lookup from Income Tracking A4:B29. Extract the numeric invoice-reference suffix only as a join key, reject duplicate or missing matches, and keep the original log invoice number as the destination number. Dates range from January 13 through November 7, 2026. The invoice-date and terms decisions are resolved; do not substitute work dates or the conversion date. Reconcile amounts directly to Time Log and Expense Log; no comparisons or exceptions based on history-page totals belong in the conversion report.

Expense Log row 11 now belongs to project 524 and invoice 667, matching the invoice's Time Log entries. The user confirmed this correction, and it is present in the saved workbook. All 26 invoice groups now have one consistent project. Apply the source correction to existing database expense 17 as part of reconciliation; no invoice-rule or schema change is needed for this association.

Generate reconstructed HTML documents with the existing renderer, verify the amounts and `{project number} - {project description}` references, and save them through the existing document convention. These are reconstructed documents, not original archived spreadsheet printouts. Stage and verify them before publishing them to the production invoices directory. Retire the backed-up test documents only as part of the reviewed conversion.

Do not create payments or applications, allocate the existing payment to the rebuilt invoices, or force invoice status to Paid. The application derives Paid status from payment applications; it will have no imported historical settlements. Preserve existing payment records without consulting history-page payment information. Removing applications to deleted test invoices releases their amounts as unapplied credit.

## 5 Precision and source corrections

| Item | Evidence | Required handling |
| --- | --- | --- |
| Customer placeholders resolved | Customers `D9:H9` now contain user-entered `na` values | Accept through current validation and retain them, with normal state uppercasing. |
| Expense date resolved | Expense Log `B26` is now a valid Excel date for March 21, 2026 | Import the corrected source date; no conversion-time date repair is needed. |
| Invoice/project association resolved | Expense Log `C11` is now project 524 with invoice 667, as confirmed by the user | Update existing database expense 17 to project 524 and link it once to the reconstructed invoice 667. |
| Time date conflict | Time Log `B34` is February 27; existing time entry 6 is February 23 | Use February 27 from the authoritative spreadsheet; discard the test invoice. |
| Zero-hour annotation | Time Log row 63 | Retain as an annotation in the conversion report; exclude from time records. |
| Fractional-cent mileage | 22 rows at $0.725: `K51`, `K52`, `K54`, `K61`, `K63`, `K73`, `K82`, `K84:K86`, `K93`, `K102`, `K105:K110`, `K114`, `K121`, `K125:K126` | Preserve the exact unit rate and each row's original mileage quantity. |
| House renovation expense | Expense Log row 67 is $94,099.09 for project 504 and references invoice 674 | Preserve the single source expense and link it once to the reconstructed invoice. |

The user approved updating expense unit-cost precision to support fractional-cent mileage allowances. Implement this as lasting expense functionality, independently of the temporary conversion. Store rates as exact integers in ten-thousandths of a dollar, for example `unit_cost_ten_thousandths = 7250` for $0.725. Migrate existing cent rates by multiplying by 100, and use one authoritative rate field rather than keeping a second rounded rate as the source of truth. Invoice and expense line totals remain integer cents.

Update the expense write model, calculations, API payloads, editor input/parser, unit-rate display, and audit export together. Unit costs must accept and preserve up to four decimal places in dollars; totals still display two. Use decimal arithmetic for quantity-times-rate and round only the final line amount. Retain regression tests for this ongoing expense feature; conversion-specific scripts and checks remain temporary. Document the lasting precision behavior in the product, workflow, and API references when implementing it.

Use decimal arithmetic from the source numeric strings. The proposed new-line policy is round-half-up to cents once per line, after multiplication. For these 124 expense rows:

| Calculation | Amount |
| --- | ---: |
| Exact sum of quantity times unit rate | $145,788.845 |
| Round that aggregate once to cents | $145,788.85 |
| Sum individually rounded decimal lines | $145,788.92 |

The seven-cent difference follows from row rounding. Seventeen additional mileage rates changed from $0.73 to $0.725 in the updated workbook. Rounding all 22 fractional-cent unit rates back to $0.73 before multiplication would yield $145,796.02, adding $7.10 compared with the proposed precise-line calculation. Preserve the exact rates instead.

Some formula caches for half-cent lines sit slightly below their exact decimal values. Do not adopt those floating-point artifacts as an accounting policy. Reconcile line amounts to the four main source sheets and any corrections supplied by the user; the history sheet supplies dates only. Existing test invoices and history-page totals are not authoritative. Final amount targets depend on the accepted rounding policy; do not force them by adding invented adjustment rows.

## 6 Temporary conversion tools

Keep the converter and its checks in a temporary working directory outside the application source tree. Use the checked-in `.venv` and standard-library ZIP/XML parsing for this specific workbook. Handle its relationships, shared/inline strings, numeric values, formula caches, table metadata, and date system. Do not build a general import framework or install global packages.

The temporary tool performs three operations: produce a read-only dry run, apply the reviewed conversion including real invoice reconstruction, and verify the result. It must not become a backend module, command shipped with the application, permanent conversion test suite, or recurring synchronization feature. The approved expense-precision feature and its normal regression tests remain in the application.

The normal CRUD helpers commit individually. Do not call them repeatedly and assume the whole conversion is atomic, and do not refactor them solely for conversion. Validate using existing domain rules, then use the normal connection setup with foreign keys enabled, parameterized writes, and existing helpers that do not commit. Commit the approved source-record corrections, removal of test invoice applications/links/invoices, and reconstructed invoice records/links in one explicit transaction. Roll back the database batch on any failure. Do not write payment records or create payment applications.

SQLite transactions do not roll back filesystem writes. Stage reconstructed HTML in the temporary directory, verify it, and coordinate publication with database commit so failures can be recovered using the recorded file list and backup. Remove only identified test document files; do not purge the invoices directory. Verify that the document GET returns the reconstructed saved HTML after conversion.

Keep source-to-target IDs, original source values, approved corrections, before-values for changed existing records, row outcomes, and reconciled totals in the final conversion report and reviewed mapping file. Include skipped annotations and reused records. No `import_batches`, `import_source_records`, or other permanent import infrastructure is needed. Archive this evidence alongside the unchanged workbook and normal application backups; the mapping/report files are separate conversion records and are not automatically included by the application's database-and-invoice ZIP backup.

Dry run must use a read-only target connection and perform no production migrations or inserts. It should emit a readable report and a machine-readable mapping with proposed inserts, reuses, corrected records, test invoice/application/document removals, reconstructed real invoices and links, unresolved source exceptions, and totals by project/category/invoice. Before apply, verify the source hash, mapping, schema, and reviewed database baseline. Refuse to apply if the baseline has changed, including after a successful prior apply. An interrupted run requires inspection and reconciliation before any retry. There is no ongoing support for new workbook versions or synchronization.

After the conversion is accepted, remove the temporary parser, writer, verification scripts, scratch data, and disposable rehearsal databases. Retain only the application data and agreed accounting evidence. The application must function correctly without any conversion code present.

## 7 Execution sequence

1. Capture the verified source snapshot and complete source-to-target mapping, including the corrected project for existing expense 17. Use the documented per-line round-half-up calculation, Net 30 terms, and verified date-only lookup for all 26 invoice groups. Process Barron's required fields, the expense date, and invoice 667's project association are resolved. Use the four main sheets for source records and amounts; do not consult other history-page fields.
2. Implement the approved expense unit-cost precision feature, its regression tests, and matching [workflow](../workflows.md), [PRD](../tims_ledger_prd.md), and [API Reference](../API%20Reference.md) updates. Create the one-time conversion tools separately in a temporary directory.
3. Rehearse the precision migration and complete conversion on a disposable, consistent SQLite copy, with a separate data directory and invoice directory. Include test invoice cleanup, source reconciliation, real invoice links, staged HTML, and checks that payment records remain unchanged. Generate the exception and reconciliation reports.
4. Review the complete expected result. The source target is 7 customers, 49 projects, 202 positive-duration time records, and 124 expenses, with one zero-hour annotation retained in the report. The starting estimate is 5 new customers, 42 new projects, 160 new time entries, and 107 new expenses, plus corrections to reused records. Reconstruct the 26 invoice groups with their matched dates, Net 30 terms, and resolved source associations.
5. At cutover, freeze spreadsheet entry and stop application writes. Create an application ZIP backup of the database and saved invoice HTML before the precision migration and conversion. Verify that it is a normal restore candidate and retain an unchanged copy of the source workbook.
6. Apply the precision migration and refresh the dry run against the resulting schema. Recheck the source hash and database baseline, then run the reviewed conversion transaction and coordinated document publication. Remove the test invoice applications, links, invoices, and identified HTML files as planned. Do not import or allocate payments.
7. Reconcile the result, inspect the affected screens and reconstructed saved invoices, and create a post-conversion application backup. Archive the final report and mapping separately. Remove all temporary conversion code and scratch files, verify the application works without them, and then resume accounting entry in the application. Record the cutover point; this is not a continuing spreadsheet import process.

For recovery, use the application's Backup & Restore workflow, which creates a safety backup first. Do not wipe the database, reseed it, or replace database/invoice files by hand. A failed conversion transaction should already have rolled back. Use the pre-conversion backup if recovery is still needed.

## 8 Acceptance checks

- Every actual source row has one recorded outcome: inserted, reused/corrected, explicitly deferred, or annotation-only. A complete conversion accounts for all 7 customers, 49 projects, 203 time source rows, 124 expense source rows, and 26 invoice groups identified in the logs.
- There are 202 positive-duration time records represented after the zero-hour annotation is excluded, assuming every overlap is resolved and no additional source corrections are required. Their source amount reconciles to $222,350.00.
- Expense amounts reconcile by project, category, and invoice to the accepted decimal/correction policy. Show the seven-cent aggregate-versus-line rounding difference explicitly. Under per-line round-half-up, the updated source total is $145,788.92. Verify that all 22 $0.725 rates and original mileage quantities survive conversion, API readback, editor use, and audit export exactly.
- Customer/project references remain consistent. No duplicate customers or alternate padded project numbers are inserted for mapped existing records. Built-in rates and custom HD rates are complete.
- No test invoices, test invoice links/applications, or identified test HTML files remain after accepted cleanup. Real invoice numbers, dates, source links, reconciled totals, terms, issue state, and saved HTML match the reviewed source evidence. Existing company settings and backup history remain intact.
- The only use of the payment/history page is the permitted invoice-date lookup, with column A used solely as the matching key and column B as the date. All 26 invoice groups have one matching date and `terms_days = 30`. No amounts, payment fields, paid flags, notes, or balances come from that page. The payment table is unchanged, and no payment applications are imported or created. Only applications referencing deleted test invoices are removed, releasing their amounts as unapplied credit. Do not force reconstructed invoices to Paid.
- Billed billable rows link to their reconstructed real invoices and remain excluded from new invoice eligibility, including the three previously unlinked database records. The office expense remains in Total Expenses and Non-Billable Expenses. Project/expense totals count each reconciled source record once.
- Temporary parser checks cover table totals and formula-only rows, a missing required formula cache, malformed dates, leading-zero ZIP/project identifiers, unknown categories, ambiguous duplicates, and missing customer/project references.
- Temporary rehearsal checks cover authoritative corrections from the four main sheets, accepted `na` customer placeholders, the corrected March 21 expense date, the bounded date-only lookup with missing/duplicate-key rejection, Net 30 terms, updating existing expense 17 to project 524/invoice 667 without duplication, zero-duration annotation, custom HD entries, fractional-cent rates, test document cleanup, reconstructed document readback, database rollback, publication failure recovery, and refusal to reapply after the reviewed baseline changes.
- Run the repository Python syntax check, `python -m unittest discover -s tests -p "test_*.py"`, and `node --test tests/frontend-phase2.test.cjs` for the lasting precision feature. Start the rehearsal app using `startup.bat` and manually verify Customers, Projects, Time, Expenses, reconstructed invoices, protected printing, new invoice source selection, business expense totals, and audit export.
- No permanent import modules, commands, tracking tables, or conversion-only helper refactors remain. Temporary scripts, checks, scratch files, and rehearsal databases are removed after verification. Conversion evidence is retained as documents, not executable application features.

The identified source-data issues were resolved before rehearsal and production conversion. The history page was used only for the explicitly permitted invoice-date lookup; payments were excluded.

## 9 Implementation and conversion results

The production conversion completed on November 7, 2026 (America/Chicago). Final counts are 7 customers, 49 projects, 154 project rates, 202 time entries, 124 expenses, and 26 issued invoices with saved HTML documents. Every invoice uses its matched date and Net 30 terms. The zero-hour source row remains an annotation in the retained mapping.

Time totals $222,350.00, expenses total $145,788.92, and reconstructed invoice charges total $368,133.92. The $5.00 office expense remains non-billable. All 22 $0.725 mileage rates retain exact precision. Existing records were reconciled rather than duplicated, including expense 17's move to project 524 and invoice 667. The six test invoices, their saved documents, and their six payment applications were removed. The company profile and existing payment record are unchanged; no payments or new payment applications were imported.

The permanent changes are migration `0004_expense_unit_cost_precision.sql`, exact expense-rate calculations/API/editor/export support, cache refresh for the expense controller, regression tests, and matching product/API/workflow documentation. No importer module, legacy invoice field, import tracking table, or conversion-only helper remains.

The backend syntax check, all 6 backend tests, and all 11 frontend checks passed. Rehearsal verified full transaction rollback, recovery from partial document publication, and refusal to repeat an applied batch. Browser checks verified the precise rate through duplicate/save, protection reset after saving, and protected saved-document printing. Production checks verified all five source/invoice APIs, all 26 saved-document GET routes, audit-export precision, SQLite integrity, foreign keys, source totals, and unchanged payment/company records. The application was restarted through `startup.bat` and verified again after temporary-tool cleanup.

Pre-conversion backup: [Tims-Ledger-Backup-2026-11-07-220813.zip](../../app-data/backups/Tims-Ledger-Backup-2026-11-07-220813.zip).

Post-conversion backup: [Tims-Ledger-Backup-2026-11-07-222655.zip](../../app-data/backups/Tims-Ledger-Backup-2026-11-07-222655.zip).

The [Conversion Report](../../app-data/conversion-2026-11-07/Conversion%20Report.md), unchanged source workbook copy, source-to-database mapping with before-values, and machine-readable receipt are retained in `app-data/conversion-2026-11-07/`. These separate accounting records are retained alongside the normal application backups. All temporary conversion scripts, scratch files, dependency link, staging files, and rehearsal databases have been removed.
