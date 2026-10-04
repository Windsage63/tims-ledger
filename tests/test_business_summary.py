"""Verify business totals against disposable SQLite records only."""
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.payments import payments_bootstrap_payload, business_summary_payload


class BusinessSummaryTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        for migration in sorted((ROOT / "migrations").glob("*.sql")):
            self.db.executescript(migration.read_text(encoding="utf-8"))
        self.addCleanup(self.db.close)

    def insert(self, table, **values):
        columns = ", ".join(values)
        placeholders = ", ".join("?" for _ in values)
        self.db.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(values.values()))

    def seed(self):
        stamp = {"created_at": "2026-10-04", "updated_at": "2026-10-04"}
        for n in (1, 2):
            self.insert("customers", id=n, customer_name=f"Customer {n}", street_address="", city="", state="", zip="", contact_name="", email="", phone="", **stamp)
            self.insert("projects", id=n, project_number=f"P{n}", customer_id=n, description="Test", default_rate_cents=10000, **stamp)
        for n, issued in ((1, "2025-01-01"), (2, "2026-01-01"), (3, None)):
            self.insert("invoices", id=n, invoice_number=f"I{n}", project_id=1, customer_id=1, invoice_date="2026-01-01", terms_days=30, issued_at=issued, **stamp)
            self.insert("time_entries", entry_date="2026-01-01", project_id=1, customer_id=1, description="Work", minutes=60, rate_code="Regular", rate_cents=10000, line_total_cents={1:10000, 2:5000, 3:9000}[n], invoice_id=n, **stamp)
        for n, cents, billable, invoice in ((1, 2000, 1, 1), (2, 1000, 1, 3), (3, 500, 0, None), (4, 1500, 0, None)):
            self.insert("expenses", id=n, entry_date="2025-01-01" if n == 4 else "2026-01-01", project_id=2 if n == 4 else 1, customer_id=2 if n == 4 else 1, vendor="Test", description="Cost", quantity=1, unit_cost_cents=cents, line_total_cents=cents, category="Misc.", is_billable=billable, invoice_id=invoice, **stamp)
        for n, cents, year in ((1, 8000, 2025), (2, 5000, 2026), (3, 2500, 2026), (4, -500, 2026), (5, 0, 2026)):
            self.insert("payments", id=n, customer_id=2 if n == 3 else 1, payment_date=f"{year}-01-01", amount_cents=cents, **stamp)
        for n, cents in ((1, 3000), (2, 5000)):
            self.insert("payment_applications", payment_id=n, invoice_id=n, applied_amount_cents=cents, applied_at="2026-10-04")

    def test_empty_database_has_zero_totals(self):
        self.assertEqual(business_summary_payload(self.db), dict(total_income_cents=0, total_open_ar_cents=0, total_expenses_cents=0, non_billable_expenses_cents=0))

    def test_totals_include_all_years_and_customers_but_exclude_draft_ar(self):
        self.seed()
        expected = dict(total_income_cents=15000, total_open_ar_cents=9000, total_expenses_cents=5000, non_billable_expenses_cents=2000)
        for year in (None, "2025", "2026", "1900"):
            with self.subTest(year=year):
                payload = payments_bootstrap_payload(self.db, year=year)
                self.assertEqual(payload["business_summary"], expected)
                if year:
                    self.assertTrue(all(p["payment_date"].startswith(year) for p in payload["payments"]))

    def test_totals_follow_persisted_changes_and_released_allocations(self):
        self.seed()
        self.db.execute("UPDATE payment_applications SET applied_amount_cents=6000 WHERE payment_id=1")
        self.assertEqual(business_summary_payload(self.db)["total_open_ar_cents"], 6000)
        self.assertEqual(business_summary_payload(self.db)["total_income_cents"], 15000)
        self.db.execute("UPDATE payments SET amount_cents=9000 WHERE id=1")
        self.assertEqual(business_summary_payload(self.db)["total_income_cents"], 16000)
        self.db.execute("DELETE FROM payment_applications WHERE payment_id=1")
        self.db.execute("DELETE FROM payments WHERE id=1")
        self.db.execute("UPDATE expenses SET is_billable=1 WHERE id=3")
        totals = business_summary_payload(self.db)
        self.assertEqual(totals, dict(total_income_cents=7000, total_open_ar_cents=12000, total_expenses_cents=5000, non_billable_expenses_cents=1500))


if __name__ == "__main__":
    unittest.main()
