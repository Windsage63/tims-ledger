# ADR 0003: Separate Payments from Payment Applications

## Status

Accepted as initial direction.

## Context

Air Advantage receives customer advances and payments that may apply to one invoice, many invoices, or no invoice yet. A single invoice paid flag cannot model partial payments, advances, credits, or overpayments reliably.

## Decision

Model payments and payment applications separately:

  - `payments` records money received or credits/adjustments.
  - `payment_applications` records how much of a payment is applied to a specific invoice.
  - Payments begin with an unapplied amount that can later be distributed across one invoice, many invoices, or left unapplied.
  - Unapplied credits are shown separately from invoice charges and affect balances through payment application records, not by rewriting invoice lines.

## Alternatives Considered

  - Store paid amount directly on invoices.
  - Use one customer ledger table only.
  - Track payments as negative invoice rows.

## Consequences

This supports advances, retainers, partial payments, multi-invoice checks, and customer credits cleanly. It requires transaction-safe service logic to prevent over-application, keep invoice open balances and payment unapplied amounts correct, and ensure customer balances remain explainable from invoices, payments, and payment applications.
