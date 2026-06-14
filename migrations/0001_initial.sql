PRAGMA foreign_keys = ON;

BEGIN;

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

CREATE TABLE project_rates (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    rate_code TEXT NOT NULL,
    rate_cents INTEGER NOT NULL CHECK (rate_cents >= 0),
    is_builtin INTEGER NOT NULL CHECK (is_builtin IN (0, 1)),
    sort_order INTEGER NOT NULL CHECK (sort_order >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT
);

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

CREATE TABLE time_entries (
    id INTEGER PRIMARY KEY,
    entry_date TEXT NOT NULL,
    project_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    minutes INTEGER NOT NULL CHECK (minutes > 0),
    rate_code TEXT NOT NULL,
    rate_cents INTEGER NOT NULL CHECK (rate_cents >= 0),
    line_total_cents INTEGER NOT NULL CHECK (line_total_cents >= 0),
    invoice_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE RESTRICT
);

CREATE TABLE expenses (
    id INTEGER PRIMARY KEY,
    entry_date TEXT NOT NULL,
    project_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    vendor TEXT NOT NULL,
    description TEXT NOT NULL,
    quantity REAL NOT NULL CHECK (quantity > 0),
    unit_cost_cents INTEGER NOT NULL CHECK (unit_cost_cents >= 0),
    line_total_cents INTEGER NOT NULL CHECK (line_total_cents >= 0),
    category TEXT NOT NULL,
    is_billable INTEGER NOT NULL CHECK (is_billable IN (0, 1)),
    invoice_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE RESTRICT
);

CREATE TABLE payments (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    payment_date TEXT NOT NULL,
    reference_number TEXT,
    amount_cents INTEGER NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
);

CREATE TABLE payment_applications (
    id INTEGER PRIMARY KEY,
    payment_id INTEGER NOT NULL,
    invoice_id INTEGER NOT NULL,
    applied_amount_cents INTEGER NOT NULL CHECK (applied_amount_cents > 0),
    applied_at TEXT NOT NULL,
    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE RESTRICT,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX ux_projects_project_number ON projects(project_number);
CREATE UNIQUE INDEX ux_invoices_invoice_number ON invoices(invoice_number);
CREATE UNIQUE INDEX ux_project_rates_project_rate_code ON project_rates(project_id, rate_code);
CREATE UNIQUE INDEX ux_payment_applications_payment_invoice ON payment_applications(payment_id, invoice_id);

CREATE INDEX idx_projects_customer_id ON projects(customer_id);
CREATE INDEX idx_project_rates_project_id ON project_rates(project_id);
CREATE INDEX idx_time_entries_project_date ON time_entries(project_id, entry_date);
CREATE INDEX idx_time_entries_customer_date ON time_entries(customer_id, entry_date);
CREATE INDEX idx_time_entries_invoice_id ON time_entries(invoice_id);
CREATE INDEX idx_expenses_project_date ON expenses(project_id, entry_date);
CREATE INDEX idx_expenses_customer_date ON expenses(customer_id, entry_date);
CREATE INDEX idx_expenses_invoice_id ON expenses(invoice_id);
CREATE INDEX idx_invoices_customer_date ON invoices(customer_id, invoice_date);
CREATE INDEX idx_invoices_project_date ON invoices(project_id, invoice_date);
CREATE INDEX idx_payments_customer_date ON payments(customer_id, payment_date);
CREATE INDEX idx_payment_applications_payment_id ON payment_applications(payment_id);
CREATE INDEX idx_payment_applications_invoice_id ON payment_applications(invoice_id);

CREATE INDEX idx_time_entries_unbilled_nonzero_rate
    ON time_entries(project_id, entry_date)
    WHERE invoice_id IS NULL AND rate_cents > 0;

CREATE INDEX idx_expenses_unbilled_billable
    ON expenses(project_id, entry_date)
    WHERE invoice_id IS NULL AND is_billable = 1;

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
