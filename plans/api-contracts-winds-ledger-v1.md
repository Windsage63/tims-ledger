# Winds Ledger API Contracts v1

## Purpose

This document defines the JSON contracts for the major Winds Ledger screens and their core write actions. The contracts are designed for a FastAPI backend with vanilla JavaScript page modules that load working datasets into memory and filter them locally.

## Global JSON Conventions

1. IDs are integers.
2. Money is represented as integer cents.
3. Time duration is represented as integer minutes.
4. Dates use `YYYY-MM-DD`.
5. Timestamps use UTC ISO 8601 strings.
6. Booleans are real JSON booleans in the API, even though SQLite stores them as integers.
7. The frontend formats money and hours for display; the API sends normalized values.

## Response Envelope

Recommended standard envelope:

```json
{
  "data": {},
  "meta": {
    "generated_at": "2026-05-31T15:22:00Z",
    "screen": "customers",
    "version": "v1"
  },
  "errors": []
}
```

Error response shape:

```json
{
  "data": null,
  "meta": {
    "version": "v1"
  },
  "errors": [
    {
      "code": "validation_error",
      "message": "Invoice number is required.",
      "field": "invoice_number"
    }
  ]
}
```

## Shared Entity Shapes

### Customer Summary Row

```json
{
  "id": 12,
  "customer_name": "Acme Corp.",
  "contact_name": "Jane Smith",
  "email": "jane@acme.com",
  "phone": "555-0100",
  "open_ar_cents": 420000,
  "net_balance_cents": 420000,
  "updated_at": "2026-05-31T15:00:00Z"
}
```

Customer badges on browse surfaces are derived from balance state. There is no stored active or inactive lifecycle flag and no stored customer status field.

### Project Row

```json
{
  "id": 33,
  "project_number": "0526",
  "customer_id": 12,
  "customer_name": "Acme Corp.",
  "description": "Stormwater review",
  "default_rate_cents": 12500,
  "rates": [
    {
      "id": 1,
      "rate_code": "ST",
      "rate_cents": 12500,
      "is_builtin": true,
      "sort_order": 1
    }
  ],
  "updated_at": "2026-05-31T15:00:00Z"
}
```

### Time Entry Row

```json
{
  "id": 401,
  "entry_date": "2026-05-20",
  "project_id": 33,
  "project_number": "0526",
  "customer_id": 12,
  "customer_name": "Acme Corp.",
  "description": "Drainage calculations",
  "minutes": 270,
  "rate_code": "ST",
  "rate_cents": 12500,
  "line_total_cents": 56250,
  "invoice_id": null,
  "updated_at": "2026-05-31T15:00:00Z"
}
```

Time billability is derived from `rate_cents`. A time row with `rate_cents` equal to `0` is non-billable and should not appear in invoice selection lists.
Invoice number is resolved by joining to the linked invoice when the UI needs a display value.

### Expense Row

```json
{
  "id": 812,
  "entry_date": "2026-05-19",
  "project_id": 33,
  "project_number": "0526",
  "customer_id": 12,
  "customer_name": "Acme Corp.",
  "vendor": "County Recorder",
  "description": "Map copy fee",
  "quantity": 2,
  "unit_cost_cents": 1500,
  "line_total_cents": 3000,
  "category": "Records",
  "is_billable": true,
  "invoice_id": null,
  "updated_at": "2026-05-31T15:00:00Z"
}
```

Expense rows keep a single invoice linkage field. Invoice number is a derived display value from the linked invoice.

### Invoice Ledger Row

```json
{
  "id": 201,
  "invoice_number": "INV-2026-014",
  "project_id": 33,
  "project_number": "0526",
  "customer_id": 12,
  "customer_name": "Acme Corp.",
  "invoice_date": "2026-05-20",
  "terms_days": 30,
  "invoice_amount_cents": 59250,
  "paid_amount_cents": 20000,
  "open_balance_cents": 39250,
  "status": "pending",
  "issued_at": "2026-05-20T14:12:00Z",
  "updated_at": "2026-05-20T14:12:00Z"
}
```

Invoice due date is derived from `invoice_date + terms_days` when the UI needs to display it.

### Payment Ledger Row

```json
{
  "id": 71,
  "customer_id": 12,
  "customer_name": "Acme Corp.",
  "payment_date": "2026-05-28",
  "reference_number": "CHK-8122",
  "amount_cents": 50000,
  "applied_amount_cents": 20000,
  "unapplied_amount_cents": 30000,
  "application_status": "partially_applied",
  "updated_at": "2026-05-31T15:00:00Z"
}
```

### Payment Application Row

```json
{
  "id": 901,
  "payment_id": 71,
  "invoice_id": 201,
  "invoice_number": "INV-2026-014",
  "applied_amount_cents": 20000,
  "applied_at": "2026-05-28T10:00:00Z"
}
```

## Screen Contracts

### 1. Customers Screen

#### Bootstrap

Endpoint:

`GET /api/customers/bootstrap`

Response:

```json
{
  "data": {
    "customers": [
      {
        "id": 12,
        "customer_name": "Acme Corp.",
        "contact_name": "Jane Smith",
        "email": "jane@acme.com",
        "phone": "555-0100",
        "open_ar_cents": 420000,
        "net_balance_cents": 420000,
        "updated_at": "2026-05-31T15:00:00Z"
      }
    ]
  },
  "meta": {
    "screen": "customers",
    "version": "v1"
  },
  "errors": []
}
```

#### Create Or Update

Create endpoint:

`POST /api/customers`

Update endpoint:

`PUT /api/customers/{id}`

Request body:

```json
{
  "customer_name": "Acme Corp.",
  "street_address": "123 Main St.",
  "city": "Austin",
  "state": "TX",
  "zip": "78701",
  "contact_name": "Jane Smith",
  "email": "jane@acme.com",
  "phone": "555-0100",
  "notes": "Prefers email invoices"
}
```

Response returns the saved customer detail plus refreshed summary values.

### 2. Projects Screen

#### Bootstrap

Endpoint:

`GET /api/projects/bootstrap`

Response contains:

1. `projects`: array of project rows with embedded rates.
2. `customers`: lightweight lookup array for dropdowns.

#### Create Or Update

Request body:

```json
{
  "project_number": "0526",
  "customer_id": 12,
  "description": "Stormwater review",
  "default_rate_cents": 12500,
  "rates": [
    {
      "rate_code": "ST",
      "rate_cents": 12500,
      "is_builtin": true,
      "sort_order": 1
    },
    {
      "rate_code": "FF1",
      "rate_cents": 250000,
      "is_builtin": false,
      "sort_order": 10
    }
  ]
}
```

### 3. Time Screen

#### Bootstrap

Endpoint:

`GET /api/time/bootstrap?year=2026`

Response contains:

1. `entries`: array of time entry rows.
2. `projects`: lightweight project lookup.
3. `customers`: lightweight customer lookup.
4. `rates_by_project`: map from `project_id` to available rate rows.

#### Create Or Update

Request body:

```json
{
  "entry_date": "2026-05-20",
  "project_id": 33,
  "description": "Drainage calculations",
  "minutes": 270,
  "rate_code": "ST"
}
```

Response should return the saved row with resolved `customer_name`, `project_number`, `rate_cents`, `line_total_cents`, and invoice linkage fields. The backend derives invoice eligibility from the resolved rate, and `rate_cents = 0` means non-billable time.

### 4. Expenses Screen

#### Bootstrap

Endpoint:

`GET /api/expenses/bootstrap?year=2026`

Response contains:

1. `expenses`: array of expense rows.
2. `projects`: lightweight project lookup.
3. `customers`: lightweight customer lookup.
4. `categories`: available category list.

#### Create Or Update

Request body:

```json
{
  "entry_date": "2026-05-19",
  "project_id": 33,
  "vendor": "County Recorder",
  "description": "Map copy fee",
  "quantity": 2,
  "unit_cost_cents": 1500,
  "category": "Records",
  "is_billable": true
}
```

Response should return the saved row with resolved `customer_name`, `project_number`, `line_total_cents`, and invoice linkage fields.

### 5. Invoice Ledger Screen

#### Bootstrap

Endpoint:

`GET /api/invoices/bootstrap?year=2026`

Response contains:

1. `invoices`: array of invoice ledger rows.
2. `status_counts`: counts by status for the tabs.

#### Create Invoice Header

Endpoint:

`POST /api/invoices`

Request body:

```json
{
  "invoice_number": "INV-2026-014",
  "project_id": 33,
  "invoice_date": "2026-05-20",
  "terms_days": 30,
  "po_number": null,
  "notes": "Thank you for your business."
}
```

Response returns the saved invoice header plus derived summary values.

### 6. Invoice Editor Screen

#### Editor Load

Endpoint:

`GET /api/invoices/{invoice_id}/editor`

Response shape:

```json
{
  "data": {
    "invoice": {
      "id": 201,
      "invoice_number": "INV-2026-014",
      "project_id": 33,
      "project_number": "0526",
      "customer_id": 12,
      "customer_name": "Acme Corp.",
      "invoice_date": "2026-05-20",
      "terms_days": 30,
      "po_number": null,
      "notes": "Thank you for your business.",
      "issued_at": null
    },
    "selected_time_entries": [],
    "selected_expenses": [],
    "eligible_time_entries": [],
    "eligible_expenses": [],
    "summary": {
      "time_total_cents": 0,
      "expense_total_cents": 0,
      "invoice_total_cents": 0,
      "prior_balance_cents": 420000,
      "open_balance_after_issue_cents": 420000
    }
  },
  "meta": {
    "screen": "invoice_editor",
    "version": "v1"
  },
  "errors": []
}
```

#### Update Item Selection

Endpoint:

`POST /api/invoices/{invoice_id}/selection`

Request body:

```json
{
  "time_entry_ids": [401, 402],
  "expense_ids": [812]
}
```

Response should return:

1. `selected_time_entries`
2. `selected_expenses`
3. refreshed `summary`

#### Issue Invoice

Endpoint:

`POST /api/invoices/{invoice_id}/issue`

Request body:

```json
{
  "invoice_date": "2026-05-20",
  "terms_days": 30,
  "po_number": null,
  "notes": "Thank you for your business."
}
```

Response should return the final invoice ledger row, updated summary, and PDF reference.

### 7. Payments Ledger Screen

#### Bootstrap

Endpoint:

`GET /api/payments/bootstrap?year=2026`

Response contains:

1. `payments`: array of payment ledger rows.
2. `customers`: lightweight customer lookup.

#### Create Or Update Payment

Request body:

```json
{
  "customer_id": 12,
  "payment_date": "2026-05-28",
  "reference_number": "CHK-8122",
  "amount_cents": 50000,
  "notes": "Partial payment"
}
```

Response returns the saved payment row with `applied_amount_cents` and `unapplied_amount_cents` recomputed.

### 8. Payment Application Screen

#### Editor Load

Endpoint:

`GET /api/payments/{payment_id}/editor`

Response contains:

1. `payment`: payment header and unapplied summary.
2. `applications`: current application rows.
3. `open_invoices`: invoice rows for the same customer with open balances.

Example response:

```json
{
  "data": {
    "payment": {
      "id": 71,
      "customer_id": 12,
      "customer_name": "Acme Corp.",
      "payment_date": "2026-05-28",
      "reference_number": "CHK-8122",
      "amount_cents": 50000,
      "applied_amount_cents": 20000,
      "unapplied_amount_cents": 30000
    },
    "applications": [
      {
        "id": 901,
        "payment_id": 71,
        "invoice_id": 201,
        "invoice_number": "INV-2026-014",
        "applied_amount_cents": 20000,
        "applied_at": "2026-05-28T10:00:00Z"
      }
    ],
    "open_invoices": [
      {
        "id": 201,
        "invoice_number": "INV-2026-014",
        "invoice_date": "2026-05-20",
        "terms_days": 30,
        "invoice_amount_cents": 59250,
        "paid_amount_cents": 20000,
        "open_balance_cents": 39250,
        "status": "pending"
      }
    ]
  },
  "meta": {
    "screen": "payment_editor",
    "version": "v1"
  },
  "errors": []
}
```

#### Replace Applications

Endpoint:

`POST /api/payments/{payment_id}/applications`

Request body:

```json
{
  "applications": [
    {
      "invoice_id": 201,
      "applied_amount_cents": 25000
    },
    {
      "invoice_id": 202,
      "applied_amount_cents": 15000
    }
  ]
}
```

Response should return:

1. refreshed `payment`
2. refreshed `applications`
3. refreshed `open_invoices`

## Mutation Response Rule

For all create and update actions, the response should return the authoritative saved object in the same shape used by the page store. That allows the frontend to patch local state directly without a mandatory full refresh.

## Page Store Guidance

Each page module should keep only the data it needs in memory.

Recommended local stores:

1. `customersStore = { customers: [] }`
2. `projectsStore = { projects: [], customers: [] }`
3. `timeStore = { entries: [], projects: [], customers: [], ratesByProject: {} }`
4. `expensesStore = { expenses: [], projects: [], customers: [], categories: [] }`
5. `invoiceLedgerStore = { invoices: [], statusCounts: {} }`
6. `invoiceEditorStore = { invoice: {}, selectedTimeEntries: [], selectedExpenses: [], eligibleTimeEntries: [], eligibleExpenses: [], summary: {} }`
7. `paymentsStore = { payments: [], customers: [] }`
8. `paymentEditorStore = { payment: {}, applications: [], openInvoices: [] }`

## Deliberate Omissions In v1

1. No GraphQL or generic query layer.
2. No client-side persistence layer such as IndexedDB.
3. No optimistic financial calculations that bypass backend validation.
4. No real-time push or websocket behavior.

## Open API Questions

1. Should the bootstrap endpoints always scope by year for time, expenses, invoices, and payments.
2. Should the API return lookup tables embedded in bootstrap responses or via shared lookup endpoints.
3. Should invoice issue be a dedicated command endpoint or an update to the invoice resource.
4. Should payment application updates replace the full application set or support incremental add and remove actions.
