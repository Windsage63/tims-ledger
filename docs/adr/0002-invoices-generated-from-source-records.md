# ADR 0002: Generate Invoices from Source Records

## Status

Accepted as initial direction.

## Context

The original workbook can produce a printable invoice, but it mixes invoice generation, invoice recordkeeping, payments, and customer balances in fragile ways. A manual invoice editor would repeat the same problem in a prettier interface.

## Decision

Invoices should be generated from approved source records:

  - billable time entries
  - reimbursable expenses
  - controlled manual adjustments when needed

When an invoice is finalized, the included source records are linked to that invoice and locked as invoiced.

## Alternatives Considered

  - Blank manual invoice editor
  - Spreadsheet-style formula-driven invoice template
  - Import-only invoice records with no source-row linkage

## Consequences

This creates a stronger audit trail and makes customer balances more reliable. It requires more careful modeling of billing statuses, draft invoices, voids, and corrections, but that complexity belongs in the application rather than in spreadsheet formulas.
