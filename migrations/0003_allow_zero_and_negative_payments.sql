PRAGMA foreign_keys = OFF;

BEGIN;

DROP VIEW IF EXISTS customer_balance_view;
DROP VIEW IF EXISTS payment_unapplied_view;

CREATE TABLE payments_rebuilt (
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

INSERT INTO payments_rebuilt (
    id,
    customer_id,
    payment_date,
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
    reference_number,
    amount_cents,
    notes,
    created_at,
    updated_at
FROM payments;

DROP TABLE payments;

ALTER TABLE payments_rebuilt RENAME TO payments;

CREATE INDEX idx_payments_customer_date ON payments(customer_id, payment_date);

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

COMMIT;

PRAGMA foreign_keys = ON;
