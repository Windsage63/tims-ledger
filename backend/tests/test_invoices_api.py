from __future__ import annotations

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

    def test_save_print_creates_invoice_assigns_rows_and_writes_html(self) -> None:
        save_response = self.client.post(
            "/api/invoices/save-print",
            json={
                "invoice": {
                    "project_id": 34,
                    "invoice_date": "2026-05-31",
                    "terms_days": 15,
                    "po_number": "PO-9902",
                    "notes": "Print after source selection.",
                },
                "time_entry_ids": [407],
                "expense_ids": [815],
            },
        )

        self.assertEqual(save_response.status_code, 200)
        save_payload = save_response.json()["data"]
        created_invoice = save_payload["invoice"]
        self.assertEqual(created_invoice["invoice_number"], "INV-2026-025")
        self.assertEqual(created_invoice["project_number"], "0527")
        self.assertEqual(created_invoice["terms_days"], 15)
        self.assertEqual(created_invoice["po_number"], "PO-9902")
        self.assertIsNotNone(created_invoice["issued_at"])
        self.assertEqual(created_invoice["status"], "printed")
        self.assertEqual(save_payload["printable_url"], f"/api/invoices/{created_invoice['id']}/document")
        self.assertEqual(save_payload["editor"]["summary"]["time_total_cents"], 27600)
        self.assertEqual(save_payload["editor"]["summary"]["expense_total_cents"], 18500)
        self.assertEqual(save_payload["editor"]["summary"]["invoice_total_cents"], 46100)

        document_response = self.client.get(save_payload["printable_url"])

        self.assertEqual(document_response.status_code, 200)
        self.assertTrue(document_response.headers["content-type"].startswith("text/html"))
        document_body = document_response.text
        self.assertIn("INV-2026-025", document_body)
        self.assertIn("Air Advantage, Inc.", document_body)
        self.assertIn("Bill To", document_body)
        self.assertIn("Services", document_body)
        self.assertIn("Expenses", document_body)
        self.assertIn("Sub-Total Invoice", document_body)
        self.assertIn("PO-9902", document_body)

        stored_invoice = self.settings.data_dir / "invoices" / f"invoice-{created_invoice['id']}-INV-2026-025.html"
        self.assertTrue(stored_invoice.exists())
        self.assertIn("INV-2026-025", stored_invoice.read_text(encoding="utf-8"))

        editor_response = self.client.get(f"/api/invoices/{created_invoice['id']}/editor")
        self.assertEqual(editor_response.status_code, 200)
        printed_invoice = editor_response.json()["data"]["invoice"]
        self.assertIsNotNone(printed_invoice["issued_at"])
        self.assertEqual(printed_invoice["status"], "printed")
        self.assertEqual(printed_invoice["pdf_file_name"], f"invoices/invoice-{created_invoice['id']}-INV-2026-025.html")

        time_bootstrap = self.client.get("/api/time/bootstrap").json()["data"]["entries"]
        assigned_time = next(entry for entry in time_bootstrap if entry["id"] == 407)
        self.assertEqual(assigned_time["invoice_number"], "INV-2026-025")

        expenses_bootstrap = self.client.get("/api/expenses/bootstrap").json()["data"]["expenses"]
        assigned_expense = next(expense for expense in expenses_bootstrap if expense["id"] == 815)
        self.assertEqual(assigned_expense["invoice_number"], "INV-2026-025")

    def test_can_edit_and_reissue_printed_invoice(self) -> None:
        save_response = self.client.post(
            "/api/invoices/save-print",
            json={
                "invoice": {
                    "id": 201,
                    "invoice_number": "INV-2026-014",
                    "project_id": 34,
                    "invoice_date": "2026-05-20",
                    "terms_days": 14,
                    "po_number": "PO-REISSUED",
                    "notes": "Updated after issue.",
                },
                "time_entry_ids": [403, 407],
                "expense_ids": [815],
            },
        )

        self.assertEqual(save_response.status_code, 200)
        save_payload = save_response.json()["data"]
        updated_invoice = save_payload["invoice"]
        self.assertEqual(updated_invoice["terms_days"], 14)
        self.assertEqual(updated_invoice["po_number"], "PO-REISSUED")
        self.assertIsNotNone(updated_invoice["issued_at"])
        selection_payload = save_payload["editor"]
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

        document_response = self.client.get("/api/invoices/201/document")

        self.assertEqual(document_response.status_code, 200)
        self.assertIn("PO-REISSUED", document_response.text)
        self.assertIn("Subdivision review filing fee.", document_response.text)

        stored_invoice = self.settings.data_dir / "invoices" / "invoice-201-INV-2026-014.html"
        self.assertTrue(stored_invoice.exists())
        self.assertIn("PO-REISSUED", stored_invoice.read_text(encoding="utf-8"))

        editor_response = self.client.get("/api/invoices/201/editor")
        self.assertEqual(editor_response.status_code, 200)
        edited_invoice = editor_response.json()["data"]["invoice"]
        self.assertEqual(edited_invoice["invoice_amount_cents"], 113375)
        self.assertEqual(edited_invoice["status"], "printed")
        self.assertIsNotNone(edited_invoice["issued_at"])
        self.assertEqual(edited_invoice["pdf_file_name"], "invoices/invoice-201-INV-2026-014.html")

        time_bootstrap = self.client.get("/api/time/bootstrap").json()["data"]["entries"]
        restored_time = next(entry for entry in time_bootstrap if entry["id"] == 403)
        added_time = next(entry for entry in time_bootstrap if entry["id"] == 407)
        self.assertEqual(restored_time["invoice_number"], "INV-2026-014")
        self.assertEqual(added_time["invoice_number"], "INV-2026-014")

    def test_editing_paid_invoice_does_not_rewrite_payment_amount(self) -> None:
        save_response = self.client.post(
            "/api/invoices/save-print",
            json={
                "invoice": {
                    "id": 188,
                    "invoice_number": "INV-2025-098",
                    "project_id": 37,
                    "invoice_date": "2025-12-17",
                    "terms_days": 30,
                    "po_number": "PW-44",
                    "notes": "Seeded to preserve invoice linkage for time entries.",
                },
                "time_entry_ids": [406],
                "expense_ids": [816, 817],
            },
        )

        self.assertEqual(save_response.status_code, 200)
        selection_payload = save_response.json()["data"]["editor"]
        self.assertEqual(selection_payload["summary"]["invoice_total_cents"], 83962)
        self.assertEqual(selection_payload["invoice"]["status"], "printed")
        self.assertEqual(selection_payload["invoice"]["open_balance_cents"], 5762)

        payment_editor_response = self.client.get("/api/payments/68/editor")

        self.assertEqual(payment_editor_response.status_code, 200)
        payment_payload = payment_editor_response.json()["data"]
        self.assertEqual(payment_payload["payment"]["amount_cents"], 78200)
        self.assertEqual(payment_payload["payment"]["applied_amount_cents"], 78200)
        self.assertEqual(payment_payload["payment"]["unapplied_amount_cents"], 0)
        self.assertEqual(payment_payload["applications"][0]["invoice_id"], 188)
        self.assertEqual(payment_payload["applications"][0]["applied_amount_cents"], 78200)

        document_response = self.client.get("/api/invoices/188/document")

        self.assertEqual(document_response.status_code, 200)
        self.assertIn("Site mileage reimbursement.", document_response.text)

        stored_invoice = self.settings.data_dir / "invoices" / "invoice-188-INV-2025-098.html"
        self.assertTrue(stored_invoice.exists())
        self.assertIn("Site mileage reimbursement.", stored_invoice.read_text(encoding="utf-8"))

        editor_response = self.client.get("/api/invoices/188/editor")
        self.assertEqual(editor_response.status_code, 200)
        paid_invoice = editor_response.json()["data"]["invoice"]
        self.assertEqual(paid_invoice["invoice_amount_cents"], 83962)
        self.assertEqual(paid_invoice["paid_amount_cents"], 78200)
        self.assertEqual(paid_invoice["status"], "printed")
        self.assertEqual(paid_invoice["pdf_file_name"], "invoices/invoice-188-INV-2025-098.html")

    def test_save_print_rejects_invoice_without_billable_rows(self) -> None:
        save_response = self.client.post(
            "/api/invoices/save-print",
            json={
                "invoice": {
                    "project_id": 34,
                    "invoice_date": "2026-05-31",
                    "terms_days": 30,
                    "po_number": None,
                    "notes": "Cannot print empty invoice.",
                },
                "time_entry_ids": [],
                "expense_ids": [],
            },
        )

        self.assertEqual(save_response.status_code, 422)
        self.assertEqual(save_response.json()["detail"], "Select at least one billable row before saving the invoice.")

    def test_document_route_is_read_only_and_requires_saved_html(self) -> None:
        missing_document = self.client.get("/api/invoices/301/document")
        self.assertEqual(missing_document.status_code, 404)

        save_response = self.client.post(
            "/api/invoices/save-print",
            json={
                "invoice": {
                    "id": 201,
                    "invoice_number": "INV-2026-014",
                    "project_id": 34,
                    "invoice_date": "2026-05-20",
                    "terms_days": 30,
                    "po_number": "PO-READONLY",
                    "notes": "Document route should not mutate.",
                },
                "time_entry_ids": [407],
                "expense_ids": [815],
            },
        )
        self.assertEqual(save_response.status_code, 200)

        before = self.client.get("/api/invoices/201/editor").json()["data"]["invoice"]
        document = self.client.get("/api/invoices/201/document")
        after = self.client.get("/api/invoices/201/editor").json()["data"]["invoice"]

        self.assertEqual(document.status_code, 200)
        self.assertEqual(before["issued_at"], after["issued_at"])
        self.assertEqual(before["updated_at"], after["updated_at"])


if __name__ == "__main__":
    unittest.main()
