from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app


class InvoicesApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.original_env = {
            "WINDS_LEDGER_DATA_DIR": os.getenv("WINDS_LEDGER_DATA_DIR"),
            "WINDS_LEDGER_DB_PATH": os.getenv("WINDS_LEDGER_DB_PATH"),
            "WINDS_LEDGER_SKIP_STARTUP_MIGRATIONS": os.getenv("WINDS_LEDGER_SKIP_STARTUP_MIGRATIONS"),
        }

        temp_path = Path(self.temp_dir.name)
        os.environ["WINDS_LEDGER_DATA_DIR"] = str(temp_path)
        os.environ["WINDS_LEDGER_DB_PATH"] = str(temp_path / "winds-ledger-test.db")
        os.environ["WINDS_LEDGER_SKIP_STARTUP_MIGRATIONS"] = "0"

        self.client_context = TestClient(create_app(load_settings()))
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.client = None
        self.client_context = None

        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def test_bootstrap_returns_seeded_invoices_and_status_counts(self) -> None:
        response = self.client.get("/api/invoices/bootstrap")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["meta"]["screen"], "invoices")
        self.assertEqual(len(payload["data"]["invoices"]), 5)
        self.assertEqual(payload["data"]["status_counts"], {
            "all": 5,
            "draft": 1,
            "pending": 2,
            "overdue": 1,
            "paid": 1,
        })
        draft_invoice = next(invoice for invoice in payload["data"]["invoices"] if invoice["id"] == 301)
        self.assertEqual(draft_invoice["invoice_amount_cents"], 309250)
        self.assertEqual(draft_invoice["due_date"], "2026-06-30")
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

    def test_create_select_and_issue_invoice(self) -> None:
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
                "notes": "Issue after source selection.",
            },
        )

        self.assertEqual(update_response.status_code, 200)
        updated_invoice = update_response.json()["data"]["invoice"]
        self.assertEqual(updated_invoice["due_date"], "2026-06-15")
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

        issue_response = self.client.post(f"/api/invoices/{created_invoice['id']}/issue")

        self.assertEqual(issue_response.status_code, 200)
        issue_payload = issue_response.json()["data"]
        self.assertIsNotNone(issue_payload["invoice"]["issued_at"])
        self.assertEqual(issue_payload["invoice"]["status"], "pending")
        self.assertEqual(issue_payload["pdf_reference"]["file_name"], "inv-2026-025.pdf")

        pdf_response = self.client.get(f"/api/invoices/{created_invoice['id']}/pdf")

        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response.headers["content-type"], "application/pdf")
        self.assertTrue(pdf_response.content.startswith(b"%PDF-1.4"))
        pdf_path = Path(self.temp_dir.name) / "invoices" / "inv-2026-025.pdf"
        self.assertTrue(pdf_path.exists())


if __name__ == "__main__":
    unittest.main()