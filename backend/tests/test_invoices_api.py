from __future__ import annotations

from pathlib import Path
import unittest

from tests.fixtures.full_ledger_db import load_full_ledger_db
from tests.support.api_test_case import ApiTestCase


class InvoicesApiTests(ApiTestCase):
    fixture_loader = load_full_ledger_db

    def test_bootstrap_returns_seeded_invoices_and_status_counts(self) -> None:
        response = self.client.get("/api/invoices/bootstrap")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["meta"]["screen"], "invoices")
        self.assertEqual(len(payload["data"]["invoices"]), 5)
        self.assertEqual(payload["data"]["status_counts"], {
            "all": 5,
            "draft": 1,
            "printed": 3,
            "paid": 1,
        })
        draft_invoice = next(invoice for invoice in payload["data"]["invoices"] if invoice["id"] == 301)
        self.assertEqual(draft_invoice["invoice_amount_cents"], 309250)
        self.assertEqual(draft_invoice["terms_days"], 30)
        self.assertEqual(draft_invoice["status"], "draft")

    def test_editor_returns_selected_and_eligible_rows(self) -> None:
        response = self.client.get("/api/invoices/301/editor")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]

        self.assertEqual(payload["invoice"]["invoice_number"], "INV-2026-023")
        self.assertEqual([entry["id"] for entry in payload["selected_time_entries"]], [401, 402])
        self.assertEqual([expense["id"] for expense in payload["selected_expenses"]], [812])
        self.assertEqual(payload["summary"]["invoice_total_cents"], 309250)
        self.assertEqual([entry["id"] for entry in payload["eligible_time_entries"]], [401, 402])

    def test_create_select_and_print_invoice(self) -> None:
        create_response = self.client.post(
            "/api/invoices",
            json={
                "project_id": 34,
                "invoice_date": "2026-05-31",
                "terms_days": 30,
                "po_number": "PO-9901",
                "notes": "Draft for remaining billable work.",
            },
        )

        self.assertEqual(create_response.status_code, 200)
        created_invoice = create_response.json()["data"]["invoice"]
        self.assertEqual(created_invoice["invoice_number"], "INV-2026-025")
        self.assertEqual(created_invoice["project_number"], "0527")

        update_response = self.client.put(
            f"/api/invoices/{created_invoice['id']}",
            json={
                "invoice_number": created_invoice["invoice_number"],
                "project_id": 34,
                "invoice_date": "2026-05-31",
                "terms_days": 15,
                "po_number": "PO-9902",
                "notes": "Print after source selection.",
            },
        )

        self.assertEqual(update_response.status_code, 200)
        updated_invoice = update_response.json()["data"]["invoice"]
        self.assertEqual(updated_invoice["terms_days"], 15)
        self.assertEqual(updated_invoice["po_number"], "PO-9902")

        selection_response = self.client.post(
            f"/api/invoices/{created_invoice['id']}/selection",
            json={
                "time_entry_ids": [407],
                "expense_ids": [815],
            },
        )

        self.assertEqual(selection_response.status_code, 200)
        selection_payload = selection_response.json()["data"]
        self.assertEqual(selection_payload["summary"]["time_total_cents"], 27600)
        self.assertEqual(selection_payload["summary"]["expense_total_cents"], 18500)
        self.assertEqual(selection_payload["summary"]["invoice_total_cents"], 46100)

        print_response = self.client.get(f"/api/invoices/{created_invoice['id']}/print")

        self.assertEqual(print_response.status_code, 200)
        self.assertTrue(print_response.headers["content-type"].startswith("text/html"))
        print_body = print_response.text
        self.assertIn("INV-2026-025", print_body)
        self.assertIn("Air Advantage, Inc.", print_body)
        self.assertIn("Bill To", print_body)
        self.assertIn("Services", print_body)
        self.assertIn("Expenses", print_body)
        self.assertIn("Sub-Total Invoice", print_body)
        self.assertIn("PO-9902", print_body)

        stored_invoice = self.settings.data_dir / "invoices" / "INV-2026-025.html"
        self.assertTrue(stored_invoice.exists())
        self.assertIn("INV-2026-025", stored_invoice.read_text(encoding="utf-8"))

        editor_response = self.client.get(f"/api/invoices/{created_invoice['id']}/editor")
        self.assertEqual(editor_response.status_code, 200)
        printed_invoice = editor_response.json()["data"]["invoice"]
        self.assertIsNotNone(printed_invoice["issued_at"])
        self.assertEqual(printed_invoice["status"], "printed")
        self.assertEqual(printed_invoice["pdf_file_name"], "invoices/INV-2026-025.html")

    def test_can_edit_and_reissue_printed_invoice(self) -> None:
        update_response = self.client.put(
            "/api/invoices/201",
            json={
                "invoice_number": "INV-2026-014",
                "project_id": 34,
                "invoice_date": "2026-05-20",
                "terms_days": 14,
                "po_number": "PO-REISSUED",
                "notes": "Updated after issue.",
            },
        )

        self.assertEqual(update_response.status_code, 200)
        updated_invoice = update_response.json()["data"]["invoice"]
        self.assertEqual(updated_invoice["terms_days"], 14)
        self.assertEqual(updated_invoice["po_number"], "PO-REISSUED")
        self.assertIsNotNone(updated_invoice["issued_at"])

        selection_response = self.client.post(
            "/api/invoices/201/selection",
            json={
                "time_entry_ids": [403, 407],
                "expense_ids": [815],
            },
        )

        self.assertEqual(selection_response.status_code, 200)
        selection_payload = selection_response.json()["data"]
        self.assertEqual(selection_payload["summary"]["time_total_cents"], 94875)
        self.assertEqual(selection_payload["summary"]["expense_total_cents"], 18500)
        self.assertEqual(selection_payload["summary"]["invoice_total_cents"], 113375)
        self.assertEqual(
            [entry["id"] for entry in selection_payload["selected_time_entries"]],
            [403, 407],
        )
        self.assertEqual(
            [expense["id"] for expense in selection_payload["selected_expenses"]],
            [815],
        )

        print_response = self.client.get("/api/invoices/201/print")

        self.assertEqual(print_response.status_code, 200)
        self.assertIn("PO-REISSUED", print_response.text)
        self.assertIn("Subdivision review filing fee.", print_response.text)

        stored_invoice = self.settings.data_dir / "invoices" / "INV-2026-014.html"
        self.assertTrue(stored_invoice.exists())
        self.assertIn("PO-REISSUED", stored_invoice.read_text(encoding="utf-8"))

        editor_response = self.client.get("/api/invoices/201/editor")
        self.assertEqual(editor_response.status_code, 200)
        edited_invoice = editor_response.json()["data"]["invoice"]
        self.assertEqual(edited_invoice["invoice_amount_cents"], 113375)
        self.assertEqual(edited_invoice["status"], "printed")
        self.assertIsNotNone(edited_invoice["issued_at"])
        self.assertEqual(edited_invoice["pdf_file_name"], "invoices/INV-2026-014.html")

    def test_editing_paid_invoice_updates_applied_payment_to_new_total(self) -> None:
        selection_response = self.client.post(
            "/api/invoices/188/selection",
            json={
                "time_entry_ids": [406],
                "expense_ids": [816, 817],
            },
        )

        self.assertEqual(selection_response.status_code, 200)
        selection_payload = selection_response.json()["data"]
        self.assertEqual(selection_payload["summary"]["invoice_total_cents"], 83962)
        self.assertEqual(selection_payload["invoice"]["status"], "paid")
        self.assertEqual(selection_payload["invoice"]["open_balance_cents"], 0)

        payment_editor_response = self.client.get("/api/payments/68/editor")

        self.assertEqual(payment_editor_response.status_code, 200)
        payment_payload = payment_editor_response.json()["data"]
        self.assertEqual(payment_payload["payment"]["amount_cents"], 83962)
        self.assertEqual(payment_payload["payment"]["applied_amount_cents"], 83962)
        self.assertEqual(payment_payload["payment"]["unapplied_amount_cents"], 0)
        self.assertEqual(payment_payload["applications"][0]["invoice_id"], 188)
        self.assertEqual(payment_payload["applications"][0]["applied_amount_cents"], 83962)

        print_response = self.client.get("/api/invoices/188/print")

        self.assertEqual(print_response.status_code, 200)
        self.assertIn("Site mileage reimbursement.", print_response.text)

        stored_invoice = self.settings.data_dir / "invoices" / "INV-2025-098.html"
        self.assertTrue(stored_invoice.exists())
        self.assertIn("Site mileage reimbursement.", stored_invoice.read_text(encoding="utf-8"))

        editor_response = self.client.get("/api/invoices/188/editor")
        self.assertEqual(editor_response.status_code, 200)
        paid_invoice = editor_response.json()["data"]["invoice"]
        self.assertEqual(paid_invoice["invoice_amount_cents"], 83962)
        self.assertEqual(paid_invoice["paid_amount_cents"], 83962)
        self.assertEqual(paid_invoice["status"], "paid")
        self.assertEqual(paid_invoice["pdf_file_name"], "invoices/INV-2025-098.html")

    def test_print_route_rejects_draft_without_billable_rows(self) -> None:
        create_response = self.client.post(
            "/api/invoices",
            json={
                "project_id": 34,
                "invoice_date": "2026-05-31",
                "terms_days": 30,
                "po_number": None,
                "notes": "Cannot print empty draft.",
            },
        )

        self.assertEqual(create_response.status_code, 200)
        created_invoice = create_response.json()["data"]["invoice"]

        print_response = self.client.get(f"/api/invoices/{created_invoice['id']}/print")

        self.assertEqual(print_response.status_code, 422)
        self.assertEqual(print_response.json()["detail"], "Select at least one billable row before printing the invoice.")

    def test_delete_draft_invoice_clears_selection(self) -> None:
        create_response = self.client.post(
            "/api/invoices",
            json={
                "project_id": 34,
                "invoice_date": "2026-05-31",
                "terms_days": 30,
                "po_number": None,
                "notes": "Delete me.",
            },
        )

        self.assertEqual(create_response.status_code, 200)
        created_invoice = create_response.json()["data"]["invoice"]

        selection_response = self.client.post(
            f"/api/invoices/{created_invoice['id']}/selection",
            json={
                "time_entry_ids": [407],
                "expense_ids": [815],
            },
        )

        self.assertEqual(selection_response.status_code, 200)

        delete_response = self.client.delete(f"/api/invoices/{created_invoice['id']}")

        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["data"]["deleted_id"], created_invoice["id"])

        deleted_editor = self.client.get(f"/api/invoices/{created_invoice['id']}/editor")
        self.assertEqual(deleted_editor.status_code, 404)

        time_bootstrap = self.client.get("/api/time/bootstrap").json()["data"]["entries"]
        restored_time = next(entry for entry in time_bootstrap if entry["id"] == 407)
        self.assertIsNone(restored_time["invoice_number"])

        expenses_bootstrap = self.client.get("/api/expenses/bootstrap").json()["data"]["expenses"]
        restored_expense = next(expense for expense in expenses_bootstrap if expense["id"] == 815)
        self.assertIsNone(restored_expense["invoice_number"])


if __name__ == "__main__":
    unittest.main()