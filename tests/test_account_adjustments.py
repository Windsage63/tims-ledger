"""Verify invoice reductions, retained credits, and fixed project ownership."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.customers import CustomerWrite, update_customer
from app.expenses import ExpenseWrite, create_expense, expense_bootstrap_payload
from app.invoices import InvoiceSavePrintWrite, fetch_invoice, save_print_invoice
from app.payments import (
    PaymentApplicationsReplace, PaymentWrite, business_summary_payload, create_payment,
    fetch_payment, replace_payment_applications, update_payment,
)
from app.projects import ProjectWrite, create_project, fetch_project, update_project
from app.reporting import accounts_receivable_report_payload
from app.time_entries import TimeEntryWrite, create_time_entry


class AccountAdjustmentTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.addCleanup(self.db.close)
        for migration in sorted((ROOT / "migrations").glob("*.sql")):
            self.db.executescript(migration.read_text(encoding="utf-8"))
        for customer_id in (1, 2):
            self.db.execute(
                "INSERT INTO customers VALUES (?, ?, 'Street', 'City', 'IL', '60601', 'Contact', 'email', 'phone', '', 'old', 'old')",
                (customer_id, f"Customer {customer_id}"),
            )
        self.project = create_project(self.db, self.project_write())
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data_dir = Path(self.temp.name)

    def project_write(self, **changes):
        return ProjectWrite(**dict(
            dict(project_number="P1", customer_id=1, description="Work", default_rate_cents=12500), **changes
        ))

    def time(self, minutes=60, project_id=None):
        return create_time_entry(self.db, TimeEntryWrite(
            entry_date="2026-11-01", project_id=project_id or self.project["id"],
            description="Work", minutes=minutes, rate_code="ST",
        ))

    def invoice(self, number, minutes=60):
        entry = self.time(minutes)
        payload = InvoiceSavePrintWrite(
            invoice=dict(invoice_number=number, project_id=self.project["id"], invoice_date="2026-11-01", terms_days=30),
            time_entry_ids=[entry["id"]],
        )
        saved = save_print_invoice(self.db, payload, self.data_dir)
        payload.invoice.id = saved["invoice"]["id"]
        return payload, saved["invoice"]

    def payment(self, amount):
        return create_payment(self.db, PaymentWrite(customer_id=1, payment_date="2026-11-02", amount_cents=amount))

    def apply(self, payment_id, *allocations):
        return replace_payment_applications(self.db, payment_id, PaymentApplicationsReplace(
            applications=[dict(invoice_id=invoice_id, applied_amount_cents=cents) for invoice_id, cents in allocations],
        ))

    def test_short_payment_leaves_charges_and_balance_open(self):
        payload, invoice = self.invoice("SHORT", 120)
        payment = self.payment(20000)
        self.apply(payment["id"], (invoice["id"], 20000))
        saved = save_print_invoice(self.db, payload, self.data_dir)["invoice"]
        self.assertEqual(saved["invoice_amount_cents"], 25000)
        self.assertEqual(saved["open_balance_cents"], 5000)
        self.assertEqual(saved["status"], "printed")

    def test_reduction_requires_user_allocation_change_before_credit_reuse_and_net_refund(self):
        payload, invoice = self.invoice("REDUCE", 120)
        payment = self.payment(30000)
        self.apply(payment["id"], (invoice["id"], 25000))
        self.assertEqual(fetch_payment(self.db, payment["id"])["unapplied_amount_cents"], 5000)

        payload.time_entry_ids = [self.time(60)["id"]]
        payload.invoice.notes = "Unsaved invoice correction"
        original_document = (self.data_dir / invoice["pdf_file_name"]).read_bytes()
        original_rows = [tuple(row) for row in self.db.execute("SELECT * FROM payment_applications ORDER BY id")]
        with self.assertRaisesRegex(ValueError, "^a paid invoice cannot be lower than the payments allocated to it$"):
            save_print_invoice(self.db, payload, self.data_dir)
        self.db.rollback()
        self.assertEqual(fetch_invoice(self.db, invoice["id"])["invoice_amount_cents"], 25000)
        self.assertNotEqual(fetch_invoice(self.db, invoice["id"])["notes"], "Unsaved invoice correction")
        self.assertEqual([tuple(row) for row in self.db.execute("SELECT * FROM payment_applications ORDER BY id")], original_rows)
        self.assertEqual((self.data_dir / invoice["pdf_file_name"]).read_bytes(), original_document)
        self.assertEqual(fetch_payment(self.db, payment["id"])["unapplied_amount_cents"], 5000)

        self.apply(payment["id"], (invoice["id"], 12500))
        saved = save_print_invoice(self.db, payload, self.data_dir)["invoice"]
        self.assertEqual(saved["paid_amount_cents"], 12500)
        self.assertEqual(saved["open_balance_cents"], 0)
        self.assertEqual(fetch_payment(self.db, payment["id"])["amount_cents"], 30000)
        self.assertEqual(fetch_payment(self.db, payment["id"])["unapplied_amount_cents"], 17500)
        statement = accounts_receivable_report_payload(self.db, 1)["statement"]["totals"]
        self.assertEqual(statement["net_balance_cents"], -17500)
        self.assertEqual(business_summary_payload(self.db)["total_open_ar_cents"], 0)

        _, future = self.invoice("FUTURE", 60)
        self.apply(payment["id"], (invoice["id"], 12500), (future["id"], 12500))
        self.assertEqual(fetch_invoice(self.db, future["id"])["open_balance_cents"], 0)
        self.assertEqual(fetch_payment(self.db, payment["id"])["unapplied_amount_cents"], 5000)
        update_payment(self.db, payment["id"], PaymentWrite(
            customer_id=1, payment_date="2026-11-02", amount_cents=25000, notes="Net after refund",
        ))
        self.assertEqual(accounts_receivable_report_payload(self.db, 1)["statement"]["totals"]["net_balance_cents"], 0)
        self.assertEqual(business_summary_payload(self.db)["total_income_cents"], 25000)

    def test_reduction_preserves_exact_user_chosen_allocations_and_other_invoices(self):
        payload, invoice = self.invoice("MULTI", 120)
        _, other = self.invoice("OTHER", 60)
        first, second = self.payment(10000), self.payment(20000)
        self.apply(first["id"], (invoice["id"], 10000))
        self.apply(second["id"], (invoice["id"], 15000), (other["id"], 5000))
        payload.time_entry_ids = [self.time(60)["id"]]
        self.apply(first["id"], (invoice["id"], 2500))
        self.apply(second["id"], (invoice["id"], 10000), (other["id"], 5000))
        chosen_rows = [tuple(row) for row in self.db.execute("SELECT * FROM payment_applications ORDER BY id")]
        save_print_invoice(self.db, payload, self.data_dir)
        self.assertEqual([tuple(row) for row in self.db.execute("SELECT * FROM payment_applications ORDER BY id")], chosen_rows)
        self.assertEqual(fetch_payment(self.db, first["id"])["unapplied_amount_cents"], 7500)
        self.assertEqual(fetch_payment(self.db, second["id"])["unapplied_amount_cents"], 5000)
        self.assertEqual(fetch_invoice(self.db, other["id"])["paid_amount_cents"], 5000)

    def test_zero_charge_reduction_requires_user_to_remove_all_applications(self):
        payload, invoice = self.invoice("ZERO", 60)
        payment = self.payment(12500)
        self.apply(payment["id"], (invoice["id"], 12500))
        expense = create_expense(self.db, ExpenseWrite(
            entry_date="2026-11-01", project_id=self.project["id"], vendor="Vendor", description="No charge",
            quantity=1, unit_cost_ten_thousandths=0, category="Misc.", is_billable=True,
        ))
        payload.time_entry_ids = []
        payload.expense_ids = [expense["id"]]
        with self.assertRaisesRegex(ValueError, "^a paid invoice cannot be lower than the payments allocated to it$"):
            save_print_invoice(self.db, payload, self.data_dir)
        self.db.rollback()
        self.assertEqual(fetch_payment(self.db, payment["id"])["applied_amount_cents"], 12500)
        self.apply(payment["id"])
        saved = save_print_invoice(self.db, payload, self.data_dir)["invoice"]
        self.assertEqual(saved["invoice_amount_cents"], 0)
        self.assertEqual(saved["paid_amount_cents"], 0)
        self.assertEqual(fetch_payment(self.db, payment["id"])["unapplied_amount_cents"], 12500)

    def test_invoice_guard_counts_expenses_and_deduplicates_selected_rows(self):
        payload, invoice = self.invoice("MIXED", 60)
        expense = create_expense(self.db, ExpenseWrite(
            entry_date="2026-11-01", project_id=self.project["id"], vendor="Vendor", description="Cost",
            quantity=1, unit_cost_ten_thousandths=500000, category="Materials", is_billable=True,
        ))
        payload.expense_ids = [expense["id"]]
        save_print_invoice(self.db, payload, self.data_dir)
        payment = self.payment(17500)
        self.apply(payment["id"], (invoice["id"], 17500))
        payload.time_entry_ids *= 2
        payload.expense_ids = []
        with self.assertRaisesRegex(ValueError, "^a paid invoice cannot be lower than the payments allocated to it$"):
            save_print_invoice(self.db, payload, self.data_dir)
        self.db.rollback()
        payload.expense_ids = [expense["id"], expense["id"]]
        saved = save_print_invoice(self.db, payload, self.data_dir)["invoice"]
        self.assertEqual(saved["invoice_amount_cents"], 17500)
        self.assertEqual(saved["paid_amount_cents"], 17500)

    def test_failed_invoice_save_preserves_user_allocations(self):
        payload, invoice = self.invoice("FAIL", 120)
        payment = self.payment(25000)
        self.apply(payment["id"], (invoice["id"], 25000))
        self.apply(payment["id"], (invoice["id"], 12500))
        chosen_rows = [tuple(row) for row in self.db.execute("SELECT * FROM payment_applications ORDER BY id")]
        payload.time_entry_ids = [self.time(60)["id"]]
        with patch("app.invoices.build_invoice_print_html", side_effect=OSError("Write unavailable")):
            with self.assertRaises(OSError):
                save_print_invoice(self.db, payload, self.data_dir)
        self.db.rollback()
        self.assertEqual(fetch_invoice(self.db, invoice["id"])["invoice_amount_cents"], 25000)
        self.assertEqual(fetch_payment(self.db, payment["id"])["unapplied_amount_cents"], 12500)
        self.assertEqual([tuple(row) for row in self.db.execute("SELECT * FROM payment_applications ORDER BY id")], chosen_rows)

    def test_fully_allocated_payment_cannot_be_reduced_until_user_changes_allocations(self):
        _, invoice = self.invoice("NET", 120)
        payment = self.payment(25000)
        self.apply(payment["id"], (invoice["id"], 25000))
        payload = PaymentWrite(customer_id=1, payment_date="2026-11-02", amount_cents=20000, notes="Net after refund")
        with self.assertRaisesRegex(ValueError, "Amount cannot be less than currently applied total"):
            update_payment(self.db, payment["id"], payload)
        self.assertEqual(fetch_payment(self.db, payment["id"])["amount_cents"], 25000)
        self.assertEqual(fetch_invoice(self.db, invoice["id"])["paid_amount_cents"], 25000)
        self.apply(payment["id"], (invoice["id"], 20000))
        updated = update_payment(self.db, payment["id"], payload)
        self.assertEqual(updated["amount_cents"], 20000)
        self.assertEqual(fetch_invoice(self.db, invoice["id"])["open_balance_cents"], 5000)

    def test_saved_project_customer_is_fixed_but_contact_edits_are_safe(self):
        with self.assertRaisesRegex(ValueError, "customer cannot be changed"):
            update_project(self.db, self.project["id"], self.project_write(customer_id=2))
        self.assertEqual(fetch_project(self.db, self.project["id"])["customer_id"], 1)
        customer = update_customer(self.db, 1, CustomerWrite(
            customer_name="Renamed customer", street_address="New address", city="City", state="IL",
            zip="60601", contact_name="New contact", email="new@example.com", phone="555-0100",
        ))
        self.assertEqual(customer["id"], 1)
        self.assertEqual(fetch_project(self.db, self.project["id"])["customer_name"], "Renamed customer")
        updated = update_project(self.db, self.project["id"], self.project_write(description="Corrected description"))
        self.assertEqual(updated["description"], "Corrected description")

    def test_invoice_cannot_carry_payment_across_customers(self):
        payload, invoice = self.invoice("MOVE", 60)
        payment = self.payment(12500)
        self.apply(payment["id"], (invoice["id"], 12500))
        other_project = create_project(self.db, self.project_write(project_number="P2", customer_id=2))
        payload.invoice.project_id = other_project["id"]
        payload.time_entry_ids = [self.time(60, other_project["id"])["id"]]
        with self.assertRaisesRegex(ValueError, "payment applications"):
            save_print_invoice(self.db, payload, self.data_dir)
        self.assertEqual(fetch_invoice(self.db, invoice["id"])["customer_id"], 1)

    def test_negative_cash_correction_can_save_without_allocations(self):
        payment = self.payment(-1000)
        self.apply(payment["id"])
        updated = update_payment(self.db, payment["id"], PaymentWrite(
            customer_id=1, payment_date="2026-11-02", amount_cents=-1000, notes="Correction",
        ))
        self.assertEqual(updated["notes"], "Correction")
        self.assertEqual(updated["unapplied_amount_cents"], -1000)

    def test_overhead_categories_are_available_and_count_toward_expenses(self):
        for category in ("Salaries", "Insurance", "Payroll Taxes"):
            create_expense(self.db, ExpenseWrite(
                entry_date="2026-11-01", project_id=self.project["id"], vendor="Business", description=category,
                quantity=1, unit_cost_ten_thousandths=1000000, category=category, is_billable=False,
            ))
        payload = expense_bootstrap_payload(self.db)
        for category in ("Salaries", "Insurance", "Payroll Taxes"):
            self.assertIn(category, payload["categories"])
        self.assertEqual(business_summary_payload(self.db)["total_expenses_cents"], 30000)


if __name__ == "__main__":
    unittest.main()
