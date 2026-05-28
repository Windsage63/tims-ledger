# ADR 0002: Generate Invoices from Source Records

## Status

Accepted as initial direction.

## Context

The original workbook can produce a printable invoice, but it mixes invoice generation, invoice recordkeeping, payments, and customer balances in fragile ways. A manual invoice editor would repeat the same problem in a prettier interface.

## Decision

Invoices should be generated from approved source records:

  - billable time entries
  - reimbursable expenses
  - approved non-hourly or fixed-fee billing lines when needed

The invoice workflow should distinguish between draft and issued states:

  - A draft invoice may be reviewed and revised before issuance.
  - Prior customer balance and unapplied credits are displayed separately from the new invoice charges.
  - When an invoice is finalized, the included source records are marked with that invoice number.
  - Issued invoices may be recalled to draft mode, edited, and reissued when corrections are needed.
  - Recalling an invoice removes its current invoice lines and clears its invoice number from the previously assigned time and expense records so reissue can follow the normal workflow.

## Alternatives Considered

  - Blank manual invoice editor
  - Spreadsheet-style formula-driven invoice template
  - Import-only invoice records with no source-row linkage

## Consequences

This matches the intended single-user spreadsheet-replacement workflow and avoids bookkeeping steps that add complexity without practical value in this context. Recalling an invoice deliberately unwinds its current issue state by removing its invoice lines and clearing invoice-number assignments from the previously linked source records, while allowing the prior PDF output to remain stored if desired. This lets reissue follow the same normal workflow as the original issuance and prevents the user from needing to edit the database directly to correct invoices.
