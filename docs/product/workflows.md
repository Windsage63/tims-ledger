# Core Workflows

## 1. Time to Invoice

1. User enters time against a customer project.
2. Time entry receives a billing status: unbilled, drafted, invoiced, paid, void, or nonbillable.
3. Invoice Builder displays eligible unbilled time.
4. User selects rows to include.
5. Draft invoice is created from selected source records.
6. Sent invoice locks those time rows as invoiced.

## 2. Expense to Invoice

1. User enters expense or uploads a receipt.
2. Expense is categorized and marked billable/reimbursable as needed.
3. Invoice Builder displays eligible reimbursable expenses.
4. User selects rows to include.
5. Draft invoice creates expense lines while preserving the original expense record.
6. Sent invoice locks those expense rows as invoiced.

## 3. Payment to Customer Balance

1. User records a payment, deposit, advance, retainer, adjustment, write-off, or refund.
2. Payment starts with an unapplied amount.
3. User applies payment to one or more invoices.
4. Invoice open balances update.
5. Customer balance shows open AR, unapplied credits, and net balance.

## 4. Receipt OCR Review

1. User uploads a receipt.
2. OCR extracts suggested merchant, date, amount, tax, payment method, and category.
3. User reviews and edits the suggestion.
4. Approved result creates or updates an expense.
5. Raw OCR data remains separate from approved accounting fields.
