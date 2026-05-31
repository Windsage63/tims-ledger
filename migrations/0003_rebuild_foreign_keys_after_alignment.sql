PRAGMA foreign_keys = OFF;

BEGIN;

DROP VIEW IF EXISTS customer_balance_view;
DROP VIEW IF EXISTS payment_unapplied_view;
DROP VIEW IF EXISTS invoice_balance_view;
DROP VIEW IF EXISTS unbilled_time_view;
DROP VIEW IF EXISTS unbilled_expenses_view;

DROP INDEX IF EXISTS idx_project_rates_project_id;
DROP INDEX IF EXISTS idx_time_entries_project_date;
DROP INDEX IF EXISTS idx_time_entries_customer_date;
DROP INDEX IF EXISTS idx_time_entries_invoice_id;
DROP INDEX IF EXISTS idx_expenses_project_date;
DROP INDEX IF EXISTS idx_expenses_customer_date;
DROP INDEX IF EXISTS idx_expenses_invoice_id;
DROP INDEX IF EXISTS idx_payments_customer_date;
DROP INDEX IF EXISTS idx_payment_applications_payment_id;
DROP INDEX IF EXISTS idx_payment_applications_invoice_id;
DROP INDEX IF EXISTS idx_time_entries_unbilled_nonzero_rate;
DROP INDEX IF EXISTS idx_expenses_unbilled_billable;

ALTER TABLE project_rates RENAME TO project_rates_old;
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
INSERT INTO project_rates (
    id,
    project_id,
    rate_code,
    rate_cents,
    is_builtin,
    sort_order,
    created_at,
    updated_at
)
SELECT
    id,
    project_id,
    rate_code,
    rate_cents,
    is_builtin,
    sort_order,
    created_at,
    updated_at
FROM project_rates_old;
DROP TABLE project_rates_old;

ALTER TABLE time_entries RENAME TO time_entries_old;
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
INSERT INTO time_entries (
    id,
    entry_date,
    project_id,
    customer_id,
    description,
    minutes,
    rate_code,
    rate_cents,
    line_total_cents,
    invoice_id,
    created_at,
    updated_at
)
SELECT
    id,
    entry_date,
    project_id,
    customer_id,
    description,
    minutes,
    rate_code,
    rate_cents,
    line_total_cents,
    invoice_id,
    created_at,
    updated_at
FROM time_entries_old;
DROP TABLE time_entries_old;

ALTER TABLE expenses RENAME TO expenses_old;
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
INSERT INTO expenses (
    id,
    entry_date,
    project_id,
    customer_id,
    vendor,
    description,
    quantity,
    unit_cost_cents,
    line_total_cents,
    category,
    is_billable,
    invoice_id,
    created_at,
    updated_at
)
SELECT
    id,
    entry_date,
    project_id,
    customer_id,
    vendor,
    description,
    quantity,
    unit_cost_cents,
    line_total_cents,
    category,
    is_billable,
    invoice_id,
    created_at,
    updated_at
FROM expenses_old;
DROP TABLE expenses_old;

ALTER TABLE payments RENAME TO payments_old;
CREATE TABLE payments (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    payment_date TEXT NOT NULL,
    payment_type TEXT NOT NULL CHECK (payment_type IN ('payment', 'advance')),
    reference_number TEXT,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
);
INSERT INTO payments (
    id,
    customer_id,
    payment_date,
    payment_type,
    reference_number,
    amount_cents,
    notes,
    created_at,
    updated_at
)
SELECT
    id,
    customer_id,
    payment_date,
    payment_type,
    reference_number,
    amount_cents,
    notes,
    created_at,
    updated_at
FROM payments_old;
DROP TABLE payments_old;

ALTER TABLE payment_applications RENAME TO payment_applications_old;
CREATE TABLE payment_applications (
    id INTEGER PRIMARY KEY,
    payment_id INTEGER NOT NULL,
    invoice_id INTEGER NOT NULL,
    applied_amount_cents INTEGER NOT NULL CHECK (applied_amount_cents > 0),
    applied_at TEXT NOT NULL,
    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE RESTRICT,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE RESTRICT
);
INSERT INTO payment_applications (
    id,
    payment_id,
    invoice_id,
    applied_amount_cents,
    applied_at
)
SELECT
    id,
    payment_id,
    invoice_id,
    applied_amount_cents,
    applied_at
FROM payment_applications_old;
DROP TABLE payment_applications_old;

CREATE UNIQUE INDEX ux_project_rates_project_rate_code ON project_rates(project_id, rate_code);
CREATE UNIQUE INDEX ux_payment_applications_payment_invoice ON payment_applications(payment_id, invoice_id);

CREATE INDEX idx_project_rates_project_id ON project_rates(project_id);
CREATE INDEX idx_time_entries_project_date ON time_entries(project_id, entry_date);
CREATE INDEX idx_time_entries_customer_date ON time_entries(customer_id, entry_date);
CREATE INDEX idx_time_entries_invoice_id ON time_entries(invoice_id);
CREATE INDEX idx_expenses_project_date ON expenses(project_id, entry_date);
CREATE INDEX idx_expenses_customer_date ON expenses(customer_id, entry_date);
CREATE INDEX idx_expenses_invoice_id ON expenses(invoice_id);
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
        p.payment_type,
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
    payment_type,
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