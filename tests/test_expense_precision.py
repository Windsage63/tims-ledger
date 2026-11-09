"""Verify exact unit rates, half-up totals, migration, and audit export in memory."""
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pydantic import ValidationError
from app.expenses import ExpenseWrite, create_expense, update_expense
from app.reporting import build_workbook_sheets


class ExpensePrecisionTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        for migration in sorted((ROOT / "migrations").glob("000[1-3]*.sql")):
            self.db.executescript(migration.read_text(encoding="utf-8"))
        self.db.execute("INSERT INTO customers VALUES (1, 'Customer', 'Street', 'City', 'FL', '00001', 'Contact', 'email', 'phone', '', 'old', 'old')")
        self.db.execute("INSERT INTO projects VALUES (1, '1', 1, 'Project', 10000, 'old', 'old')")

    def migrate(self):
        self.db.executescript((ROOT / "migrations/0004_expense_unit_cost_precision.sql").read_text(encoding="utf-8"))

    def payload(self, **overrides):
        return ExpenseWrite(**dict(entry_date="2026-11-07", project_id=1, vendor="Vendor", description="Mileage", quantity=41, unit_cost_ten_thousandths=7250, category="Mileage", is_billable=True, **overrides))

    def test_migration_preserves_existing_money_links_and_views(self):
        self.db.execute("INSERT INTO invoices (id, invoice_number, project_id, customer_id, invoice_date, terms_days, issued_at, created_at, updated_at) VALUES (1, 'I1', 1, 1, '2026-01-01', 30, '2026-01-01', 'old', 'old')")
        self.db.execute("INSERT INTO expenses VALUES (1, '2026-01-01', 1, 1, 'Vendor', 'Hotel', 1, 17489, 17489, 'Lodging', 1, 1, 'old', 'old')")
        self.migrate()
        row = self.db.execute("SELECT * FROM expenses").fetchone()
        self.assertEqual((row['id'], row['unit_cost_ten_thousandths'], row['line_total_cents'], row['invoice_id']), (1, 1748900, 17489, 1))
        self.assertEqual(self.db.execute("SELECT invoice_amount_cents FROM invoice_balance_view").fetchone()[0], 17489)
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_half_cent_rates_round_once_after_multiplication_and_roundtrip(self):
        self.migrate()
        for quantity, rate, expected in [(41,7250,2973),(165,7250,11963),(30,7250,2175),(1,50,1),(.25,16100,40),(1,0,0)]:
            with self.subTest(quantity=quantity, rate=rate):
                values = self.payload().model_dump()
                values.update(quantity=quantity, unit_cost_ten_thousandths=rate)
                saved = create_expense(self.db, ExpenseWrite(**values))
                self.assertEqual(saved['unit_cost_ten_thousandths'], rate)
                self.assertEqual(saved['line_total_cents'], expected)
        saved = update_expense(self.db, saved['id'], self.payload())
        self.assertEqual(saved['line_total_cents'], 2973)
        sheet = dict(build_workbook_sheets(self.db))['Expenses']
        rate_col = sheet[0].index('unit_cost_ten_thousandths')
        dollars_col = sheet[0].index('unit_cost_dollars')
        self.assertTrue(any(r[rate_col] == 7250 and r[dollars_col] == .725 for r in sheet[1:]))

    def test_invalid_rate_or_quantity_is_rejected_and_printed_rows_stay_locked(self):
        self.migrate()
        for field, value in [('unit_cost_ten_thousandths',7250.5),('unit_cost_ten_thousandths',True),('unit_cost_ten_thousandths',-1),('quantity',float('inf')),('quantity',float('nan')),('quantity',0)]:
            with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                values = self.payload().model_dump()
                values[field] = value
                ExpenseWrite(**values)
        saved = create_expense(self.db, self.payload())
        self.db.execute("INSERT INTO invoices (id, invoice_number, project_id, customer_id, invoice_date, terms_days, issued_at, created_at, updated_at) VALUES (1, 'I1', 1, 1, '2026-01-01', 30, '2026-01-01', 'old', 'old')")
        self.db.execute("UPDATE expenses SET invoice_id=1 WHERE id=?", (saved['id'],))
        with self.assertRaisesRegex(ValueError, 'delete the invoice'):
            update_expense(self.db, saved['id'], self.payload())


if __name__ == '__main__':
    unittest.main()
