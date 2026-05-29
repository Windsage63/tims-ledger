# ADR 0002: Generate Invoices from Source Records

## Status

Accepted as initial direction.

## Context

The original workbook can produce a printable invoice, but it mixes invoice generation, invoice recordkeeping, payments, and customer balances in fragile ways. A manual invoice editor would repeat the same problem in a prettier interface.

The approved workflow in `docs/architecture/workflows.md` is the governing source of truth. This ADR records the architectural interpretation of that workflow and must be updated if the workflow changes.

## Decision

Invoices should be generated from approved source records:

  - billable time entries
  - reimbursable expenses
  - approved non-hourly or fixed-fee billing lines when needed

The invoice workflow should keep invoice building source-record driven while treating issue as a lightweight publish step:

  - A working invoice may be reviewed and revised before issuance.
  - Prior customer balance and unapplied credits are displayed separately from the new invoice charges.
  - Selecting a source row into an invoice assigns that row to the invoice immediately.
  - Removing a source row from an invoice clears that assignment and returns the row to the unbilled pool.
  - When an invoice is issued, the system adds or updates that invoice in the invoice listing and generates or overwrites the current PDF.
  - Issued invoices remain editable, and reissuing refreshes the invoice listing entry and current PDF rather than requiring a separate recall workflow.

## Alternatives Considered

  - Blank manual invoice editor
  - Spreadsheet-style formula-driven invoice template
  - Import-only invoice records with no source-row linkage

## Consequences

This matches the intended single-user spreadsheet-replacement workflow and avoids bookkeeping steps that add complexity without practical value in this context. It also simplifies invoice editing because the checkbox itself becomes the assignment mechanism for source rows and issuing the invoice does not need to reshuffle those assignments. In the database, the source row should carry the linked invoice ID rather than duplicated invoice-number text so invoice renumbering remains safe. The current workflow only requires the invoice listing entry and current PDF to be refreshed when an invoice is issued or reissued.
