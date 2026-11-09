"""Verify invoice charges stay separate from account balances using disposable data."""
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.invoices import InvoiceSavePrintWrite, invoice_new_editor_payload, save_print_invoice
from app.payments import (
    PaymentApplicationsReplace, PaymentWrite, create_payment, replace_payment_applications,
)
from app.projects import ProjectWrite, create_project
from app.reporting import accounts_receivable_report_payload, build_open_invoice_sheet
from app.time_entries import TimeEntryWrite, create_time_entry


class InvoiceTotalTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.addCleanup(self.db.close)
        for migration in sorted((ROOT / "migrations").glob("*.sql")):
            self.db.executescript(migration.read_text(encoding="utf-8"))
        self.db.execute("INSERT INTO customers VALUES (1, 'Customer', 'Street', 'City', 'FL', '00001', 'Contact', 'email', 'phone', '', 'old', 'old')")
        self.project = create_project(self.db, ProjectWrite(
            project_number="518", customer_id=1, description="General Office", default_rate_cents=12500,
        ))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data_dir = Path(self.temp.name)

    def invoice(self, number, minutes):
        entry = create_time_entry(self.db, TimeEntryWrite(
            entry_date="2026-08-24", project_id=self.project["id"],
            description="Drawing", minutes=minutes, rate_code="ST",
        ))
        payload = InvoiceSavePrintWrite(
            invoice=dict(invoice_number=number, project_id=self.project["id"],
                         invoice_date="2026-08-24", terms_days=30),
            time_entry_ids=[entry["id"]],
        )
        saved = save_print_invoice(self.db, payload, self.data_dir)
        payload.invoice.id = saved["invoice"]["id"]
        return payload, saved

    def test_charge_total_survives_other_invoices_credit_and_partial_or_full_payment(self):
        self.invoice("680", 600)
        self.invoice("681", 1200)
        payload, saved = self.invoice("682", 360)
        invoice_id = saved["invoice"]["id"]
        payment = create_payment(self.db, PaymentWrite(
            customer_id=1, payment_date="2026-08-25", amount_cents=10000000,
        ))

        for applied in (0, 30000, 75000):
            with self.subTest(applied=applied):
                replace_payment_applications(self.db, payment["id"], PaymentApplicationsReplace(
                    applications=[dict(invoice_id=invoice_id, applied_amount_cents=applied)] if applied else [],
                ))
                saved = save_print_invoice(self.db, payload, self.data_dir)
                invoice = saved["invoice"]
                self.assertEqual(saved["editor"]["summary"], dict(
                    time_total_cents=75000, expense_total_cents=0, invoice_total_cents=75000,
                ))
                self.assertEqual(invoice["paid_amount_cents"], applied)
                self.assertEqual(invoice["open_balance_cents"], 75000 - applied)
                self.assertEqual(invoice["status"], "paid" if applied == 75000 else "printed")
                document = (self.data_dir / invoice["pdf_file_name"]).read_text(encoding="utf-8")
                summary = re.search(r'<table class="summary-table">(.*?)</table>', document, re.S)[1]
                self.assertEqual(re.findall(r'<tr><td>(.*?)</td><td class="numeric">(.*?)</td></tr>', summary),
                                 [("Total Invoice", "$750.00")])
                for label in ("Sub-Total Invoice", "Prior Balance", "Unapplied Credit", "Total Due"):
                    self.assertNotIn(label, document)
                self.assertIn("518 - General Office", document)

                statement = accounts_receivable_report_payload(self.db, 1)["statement"]
                self.assertEqual(statement["totals"]["open_ar_cents"], 450000 - applied)
                self.assertEqual(statement["totals"]["unapplied_credit_cents"], 10000000 - applied)
                self.assertEqual(statement["totals"]["net_balance_cents"], -9550000)
                sheet = build_open_invoice_sheet(self.db)
                audit = next(dict(zip(sheet[0], row)) for row in sheet[1:] if row[0] == invoice_id)
                self.assertEqual(audit["invoice_amount_cents"], 75000)
                self.assertEqual(audit["paid_amount_cents"], applied)
                self.assertEqual(audit["open_balance_cents"], 75000 - applied)
                self.assertEqual(audit["prior_balance_cents"], 375000)
                self.assertEqual(audit["unapplied_credit_cents"], 10000000 - applied)

    def test_new_editor_summary_has_only_charge_totals_despite_existing_account_balance(self):
        self.invoice("681", 600)
        create_payment(self.db, PaymentWrite(
            customer_id=1, payment_date="2026-08-25", amount_cents=10000000,
        ))
        editor = invoice_new_editor_payload(self.db, project_id=self.project["id"], invoice_date="2026-08-26")
        self.assertEqual(editor["summary"], dict(
            time_total_cents=0, expense_total_cents=0, invoice_total_cents=0,
        ))
        self.assertEqual(editor["invoice"]["prior_balance_cents"], 125000)


if __name__ == "__main__":
    unittest.main()
