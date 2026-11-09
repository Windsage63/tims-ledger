"""Exercise record deletion, released invoice sources, and ordinary zero prices."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.customers import delete_customer
from app.projects import ProjectWrite, create_project, delete_project
from app.time_entries import TimeEntryWrite, create_time_entry, delete_time_entry
from app.expenses import ExpenseWrite, create_expense, delete_expense
from app.invoices import (
    InvoiceSavePrintWrite, delete_invoice, fetch_eligible_time_entries,
    save_print_invoice,
)
from app.payments import PaymentWrite, create_payment


class RecordDeletionTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.addCleanup(self.db.close)
        for migration in sorted((ROOT / "migrations").glob("*.sql")):
            self.db.executescript(migration.read_text(encoding="utf-8"))
        self.db.execute("INSERT INTO customers VALUES (1, 'Customer', 'Street', 'City', 'FL', '00001', 'Contact', 'email', 'phone', '', 'old', 'old')")
        self.project = create_project(self.db, ProjectWrite(project_number="1", customer_id=1, description="Project", default_rate_cents=0))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data_dir = Path(self.temp.name)

    def time(self):
        return create_time_entry(self.db, TimeEntryWrite(entry_date="2026-11-08", project_id=self.project["id"], description="Work", minutes=60, rate_code="ST"))

    def expense(self):
        return create_expense(self.db, ExpenseWrite(entry_date="2026-11-08", project_id=self.project["id"], vendor="Vendor", description="Materials", quantity=1, unit_cost_ten_thousandths=10000, category="Materials", is_billable=True))

    def invoice(self, time_ids=(), expense_ids=(), number="I1"):
        return save_print_invoice(self.db, InvoiceSavePrintWrite(invoice=dict(invoice_number=number, project_id=self.project["id"], invoice_date="2026-11-08", terms_days=30), time_entry_ids=list(time_ids), expense_ids=list(expense_ids)), self.data_dir)

    def test_zero_price_time_is_eligible_and_can_make_zero_total_invoice(self):
        entry = self.time()
        self.assertEqual([row["id"] for row in fetch_eligible_time_entries(self.db, {"project_id":self.project["id"], "id":None})], [entry["id"]])
        self.assertEqual(self.db.execute("SELECT id FROM unbilled_time_view").fetchone()[0], entry["id"])
        invoice = self.invoice([entry["id"]])["invoice"]
        self.assertEqual(invoice["invoice_amount_cents"], 0)
        self.assertEqual(invoice["status"], "paid")
        self.assertTrue((self.data_dir / invoice["pdf_file_name"]).exists())
        self.assertEqual(self.db.execute("SELECT count(*) FROM unbilled_time_view").fetchone()[0], 0)

    def test_empty_invoice_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            self.invoice()
        self.db.rollback()

    def test_delete_invoice_releases_sources_and_only_its_applications(self):
        entry, expense = self.time(), self.expense()
        invoice = self.invoice([entry["id"]], [expense["id"]])["invoice"]
        other = self.invoice([self.time()["id"]], number="I2")["invoice"]
        payment = create_payment(self.db, PaymentWrite(customer_id=1, payment_date="2026-11-08", amount_cents=200))
        self.db.execute("INSERT INTO payment_applications (payment_id, invoice_id, applied_amount_cents, applied_at) VALUES (?, ?, 50, 'old')", (payment["id"], invoice["id"]))
        self.db.execute("INSERT INTO payment_applications (payment_id, invoice_id, applied_amount_cents, applied_at) VALUES (?, ?, 50, 'old')", (payment["id"], other["id"]))
        self.db.commit()
        payment_before = tuple(self.db.execute("SELECT * FROM payments").fetchone())
        self.assertTrue(delete_invoice(self.db, invoice["id"], self.data_dir))
        self.assertIsNone(self.db.execute("SELECT invoice_id FROM time_entries WHERE id=?", (entry["id"],)).fetchone()[0])
        self.assertIsNone(self.db.execute("SELECT invoice_id FROM expenses WHERE id=?", (expense["id"],)).fetchone()[0])
        self.assertEqual(tuple(self.db.execute("SELECT * FROM payments").fetchone()), payment_before)
        self.assertEqual(self.db.execute("SELECT invoice_id FROM payment_applications").fetchone()[0], other["id"])
        self.assertFalse((self.data_dir / invoice["pdf_file_name"]).exists())
        self.assertTrue((self.data_dir / other["pdf_file_name"]).exists())
        self.assertTrue(delete_time_entry(self.db, entry["id"]))
        self.assertTrue(delete_expense(self.db, expense["id"]))

    def test_document_failure_rolls_back_invoice_and_source_links(self):
        entry = self.time()
        invoice = self.invoice([entry["id"]])["invoice"]
        with patch.object(Path, "unlink", side_effect=PermissionError("locked")):
            with self.assertRaises(PermissionError):
                delete_invoice(self.db, invoice["id"], self.data_dir)
        self.assertEqual(self.db.execute("SELECT invoice_id FROM time_entries").fetchone()[0], invoice["id"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM invoices").fetchone()[0], 1)
        self.assertTrue((self.data_dir / invoice["pdf_file_name"]).exists())

    def test_invalid_document_path_cannot_delete_other_files(self):
        invoice = self.invoice([self.time()["id"]])["invoice"]
        outside = self.data_dir / "keep.txt"
        outside.write_text("keep")
        self.db.execute("UPDATE invoices SET pdf_file_name='keep.txt'")
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "path is invalid"):
            delete_invoice(self.db, invoice["id"], self.data_dir)
        self.assertEqual(outside.read_text(), "keep")

    def test_dependencies_block_deletion_even_for_zero_value_activity(self):
        entry, expense = self.time(), self.expense()
        with self.assertRaises(ValueError):
            delete_project(self.db, self.project["id"])
        with self.assertRaises(ValueError):
            delete_customer(self.db, 1)
        self.invoice([entry["id"]], [expense["id"]])
        with self.assertRaisesRegex(ValueError, "invoice"):
            delete_time_entry(self.db, entry["id"])
        with self.assertRaisesRegex(ValueError, "invoice"):
            delete_expense(self.db, expense["id"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM time_entries").fetchone()[0], 1)

    def test_unused_project_rates_and_customer_can_be_deleted(self):
        self.assertTrue(delete_project(self.db, self.project["id"]))
        self.assertEqual(self.db.execute("SELECT count(*) FROM project_rates").fetchone()[0], 0)
        self.assertTrue(delete_customer(self.db, 1))
        for helper in (delete_project, delete_customer, delete_time_entry, delete_expense):
            self.assertFalse(helper(self.db, 999))
        self.assertFalse(delete_invoice(self.db, 999, self.data_dir))


if __name__ == "__main__":
    unittest.main()
