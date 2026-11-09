BEGIN;
DROP INDEX IF EXISTS idx_time_entries_unbilled_nonzero_rate;
CREATE INDEX idx_time_entries_unbilled ON time_entries(project_id, entry_date) WHERE invoice_id IS NULL;
DROP VIEW unbilled_time_view;
CREATE VIEW unbilled_time_view AS SELECT * FROM time_entries WHERE invoice_id IS NULL;
COMMIT;
