PRAGMA foreign_keys = OFF;

BEGIN;

DROP VIEW IF EXISTS customer_balance_view;
DROP VIEW IF EXISTS payment_unapplied_view;
DROP VIEW IF EXISTS invoice_balance_view;
DROP VIEW IF EXISTS unbilled_time_view;
DROP VIEW IF EXISTS unbilled_expenses_view;

DROP INDEX IF EXISTS idx_invoices_issued_date;

ALTER TABLE customers RENAME TO customers_old;

CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    street_address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    zip TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

INSERT INTO customers (
    id,
    customer_name,
    street_address,
    city,
    state,
    zip,
    contact_name,
    email,
    phone,
    notes,
    created_at,
    updated_at
)
SELECT
    id,
    customer_name,
    street_address,
    city,
    state,
    zip,
    contact_name,
    email,
    phone,
    notes,
    created_at,
    updated_at
FROM customers_old;

DROP TABLE customers_old;

ALTER TABLE projects RENAME TO projects_old;

CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    project_number TEXT NOT NULL,
    customer_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    default_rate_cents INTEGER NOT NULL CHECK (default_rate_cents >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
);

INSERT INTO projects (
    id,
    project_number,
    customer_id,
    description,
    default_rate_cents,
    created_at,
    updated_at
)
SELECT
    id,
    project_number,
    customer_id,
    description,
    default_rate_cents,
    created_at,
    updated_at
FROM projects_old;

DROP TABLE projects_old;

ALTER TABLE invoices RENAME TO invoices_old;

CREATE TABLE invoices (
    id INTEGER PRIMARY KEY,
    invoice_number TEXT NOT NULL,
    project_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    invoice_date TEXT NOT NULL,
    terms_days INTEGER NOT NULL DEFAULT 0 CHECK (terms_days >= 0),
    po_number TEXT,
    notes TEXT,
    pdf_file_name TEXT,
    issued_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
);

INSERT INTO invoices (
    id,
    invoice_number,
    project_id,
    customer_id,
    invoice_date,
    terms_days,
    po_number,
    notes,
    pdf_file_name,
    issued_at,
    created_at,
    updated_at
)
SELECT
    id,
    invoice_number,
    project_id,
    customer_id,
    invoice_date,
    0,
    po_number,
    notes,
    pdf_file_name,
    issued_at,
    created_at,
    updated_at
FROM invoices_old;

DROP TABLE invoices_old;

CREATE UNIQUE INDEX ux_projects_project_number ON projects(project_number);
CREATE UNIQUE INDEX ux_invoices_invoice_number ON invoices(invoice_number);
CREATE INDEX idx_projects_customer_id ON projects(customer_id);
CREATE INDEX idx_invoices_customer_date ON invoices(customer_id, invoice_date);
CREATE INDEX idx_invoices_project_date ON invoices(project_id, invoice_date);

CREATE VIEW invoice_balance_view AS
WITH invoice_totals AS (
    SELECT
        i.id AS invoice_id,
        i.invoice_number,
        i.customer_id,
        i.project_id,
        COALESCE((
            SELECT SUM(te.line_total_cents)
            FROM time_entries te
            WHERE te.invoice_id = i.id
        ), 0) AS time_amount_cents,
        COALESCE((
            SELECT SUM(e.line_total_cents)
            FROM expenses e
            WHERE e.invoice_id = i.id
        ), 0) AS expense_amount_cents,
        COALESCE((
            SELECT SUM(pa.applied_amount_cents)
            FROM payment_applications pa
            WHERE pa.invoice_id = i.id
        ), 0) AS paid_amount_cents
    FROM invoices i
)
SELECT
    invoice_id,
    invoice_number,
    customer_id,
    project_id,
    time_amount_cents,
    expense_amount_cents,
    paid_amount_cents,
    time_amount_cents + expense_amount_cents AS invoice_amount_cents,
    time_amount_cents + expense_amount_cents - paid_amount_cents AS open_amount_cents
FROM invoice_totals;

CREATE VIEW payment_unapplied_view AS
WITH payment_totals AS (
    SELECT
        p.id AS payment_id,
        p.customer_id,
        p.amount_cents,
        COALESCE((
            SELECT SUM(pa.applied_amount_cents)
            FROM payment_applications pa
            WHERE pa.payment_id = p.id
        ), 0) AS applied_amount_cents
    FROM payments p
)
SELECT
    payment_id,
    customer_id,
    amount_cents,
    applied_amount_cents,
    amount_cents - applied_amount_cents AS unapplied_amount_cents
FROM payment_totals;

CREATE VIEW customer_balance_view AS
WITH customer_totals AS (
    SELECT
        c.id AS customer_id,
        COALESCE((
            SELECT SUM(ibv.open_amount_cents)
            FROM invoice_balance_view ibv
            WHERE ibv.customer_id = c.id
        ), 0) AS open_ar_cents,
        COALESCE((
            SELECT SUM(puv.unapplied_amount_cents)
            FROM payment_unapplied_view puv
            WHERE puv.customer_id = c.id
        ), 0) AS unapplied_credit_cents
    FROM customers c
)
SELECT
    customer_id,
    open_ar_cents,
    unapplied_credit_cents,
    open_ar_cents - unapplied_credit_cents AS net_balance_cents
FROM customer_totals;

CREATE VIEW unbilled_time_view AS
SELECT *
FROM time_entries
WHERE invoice_id IS NULL AND rate_cents > 0;

CREATE VIEW unbilled_expenses_view AS
SELECT *
FROM expenses
WHERE invoice_id IS NULL AND is_billable = 1;

COMMIT;

PRAGMA foreign_keys = ON;