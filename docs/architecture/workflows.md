# Core Workflows

## 1. User Enters Customer

1. User creates or updates a customer master record before entering project work.
2. User enters the customer information as follows:
    - customer_name
    - customer_street_address
    - customer_city
    - customer_state
    - customer_zip
    - customer_contact
    - customer_email
    - customer_phone
3. System validates that the customer record is complete enough for project and invoice use.
4. System stores the customer record that can be reused by other modules.
5. Customer record becomes available for the creation of projects and invoices, the receipt of payments, and the tracking of the customer account balance.

## 2. User Enters Project

1. User creates a project under an existing customer.
2. User enters the project information as follows:
    - project_number (must be unique)
    - customer_name (from dropdown)
    - project_description
    - project_default_rate
    - project_fixed_fee
3. User configures rates. Built in rates include:
    - ST = 1.0 x project_default_rate
    - OT = 1.5 x project_default_rate
    - TT = 0.5 x project_default_rate
    - HD = user-entered non-hourly billing line for fixed-fee, lump-sum, or per-each billing.
    - custom rates as entered by user. Custom rates are stored to the project.
4. System validates that project_number is unique and that the project is linked to one customer.
5. System stores the project record. Each project is linked to only one customer.
6. Project record becomes available for the entry of time, expenses, invoices, and payments.
7. If project_fixed_fee is used, the default rate may be set to 0 to allow time to be allocated and expense records may still be tracked for cost and audit purposes without automatically becoming billable invoice lines.

## 3. User Enters Time

1. User enters the date.
2. User selects the project by project number. The system derives the customer and available rates from the project record.
3. User enters the work description, number of hours, and selects the rate.
4. System stores the time entry as a source record.
5. Invoice linkage is empty until the time entry checkbox is selected into an invoice.
6. Unbilled billable time (time with no invoice linkage and a billable rate) is eligible for invoice building. When selected into an invoice, the time entry is stamped to that invoice immediately. When unselected, that invoice linkage is removed immediately. Non-billable or fixed-fee-supporting hours remain available for project tracking without being treated as labor revenue.

## 4. User Enters Expense

1. User enters the date.
2. User selects the project by project number. The system derives the customer from the project record.
3. User enters expense vendor, description, quantity, unit cost, and selects the expense category, and billable flag.
4. System stores the expense as a source record.
5. Invoice linkage is empty until the expense is selected into an invoice.
6. Unbilled billable expenses (expenses with no invoice linkage that are flagged as billable) are eligible for invoice building. When selected into an invoice, the expense is stamped to that invoice immediately. When unselected, that invoice linkage is removed immediately. Non-billable or fixed-fee-supporting expenses remain available for internal cost tracking.

## 5. User Creates an Invoice

1. User enters the date, a unique invoice number and a project number.
2. System validates that the invoice number is unique.
3. System creates a listing of all eligible unbilled time assigned to the project, showing the date, description, number of hours, rate, and total cost for each line, plus a checkbox labeled `invoice?`.
4. System creates a listing of all eligible unbilled expenses assigned to the project, showing the date, description, expense category, unit cost, and total cost for each line, plus a checkbox labeled `invoice?`.
5. If the project uses fixed-fee or non-hourly billing, the draft may also include approved HD or other controlled manual billing lines.
6. User selects the time, expense, and approved non-hourly lines to be assigned to the invoice.
7. As each line is selected, the system stamps that source record to the invoice immediately and calculates updated invoice totals.
8. Prior customer balance is shown separately from the current invoice charges. Unapplied credits may be displayed and optionally applied through payment application logic, not by rewriting invoice lines.
9. The user may review, add, or remove eligible source records. Removing a selected line clears that source record from the invoice immediately and returns it to the unbilled pool.
10. When the user issues the invoice, the system adds or updates that invoice in the invoice listing, generates the PDF, and stores or overwrites the current invoice PDF.
11. Existing issued invoices may be viewed and printed by invoice number, and they remain editable.
12. If the user edits an issued invoice, the same line-by-line checkbox workflow applies: added lines are stamped immediately, removed lines are unstamped immediately, and reissuing updates the invoice listing entry and overwrites the current PDF.

## 6. User Records and Applies a Payment

1. User records a payment, deposit, advance, or refund for a customer.
2. System creates a payment record with a full unapplied amount.
3. User applies some or all of that payment to one or more open invoices.
4. System prevents over-application and updates both invoice open balances and the payment's remaining unapplied amount.
5. Customer balance shows open AR, unapplied credits, and net balance, each explainable from invoices, payments, and payment applications.

## 7. Receipt OCR Review

1. User uploads a receipt.
2. OCR extracts suggested merchant, date, amount, and category.
3. System shows the OCR result as a suggestion that requires review.
4. User reviews and edits the suggestion.
5. Approved result creates or updates an expense.
6. Raw OCR data remains separate from approved accounting fields.
7. Images of receipts for billed expenses may be attached as separate pages to the invoice PDF when that invoice is generated.
