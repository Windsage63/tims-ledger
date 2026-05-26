# ADR 0003: Separate Payments from Payment Applications

## Status

Accepted as initial direction.

## Context

Air Advantage receives customer advances and payments that may apply to one invoice, many invoices, or no invoice yet. A single invoice paid flag cannot model partial payments, advances, credits, or overpayments reliably.

## Decision

Model payments and payment applications separately:

  - `payments` records money received or credits/adjustments.
  - `payment_applications` records how much of a payment is applied to a specific invoice.

## Alternatives Considered

  - Store paid amount directly on invoices.
  - Use one customer ledger table only.
  - Track payments as negative invoice rows.

## Consequences

This supports advances, retainers, partial payments, and multi-invoice checks cleanly. It requires transaction-safe service logic to prevent over-application and to keep invoice open balances and payment unapplied amounts correct.
