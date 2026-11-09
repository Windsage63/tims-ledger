BEGIN;

ALTER TABLE expenses RENAME COLUMN unit_cost_cents TO unit_cost_ten_thousandths;

UPDATE expenses
SET unit_cost_ten_thousandths = unit_cost_ten_thousandths * 100;

COMMIT;
