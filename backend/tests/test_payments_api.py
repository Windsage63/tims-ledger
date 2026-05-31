from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app


class PaymentsApiTests(unittest.TestCase):
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

    def test_bootstrap_returns_seeded_payments_and_customers(self) -> None:
        response = self.client.get("/api/payments/bootstrap")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["meta"]["screen"], "payments")
        self.assertEqual(len(payload["data"]["payments"]), 6)
        self.assertEqual(len(payload["data"]["customers"]), 6)
        advance_payment = next(payment for payment in payload["data"]["payments"] if payment["id"] == 71)
        self.assertEqual(advance_payment["payment_type"], "advance")
        self.assertEqual(advance_payment["application_status"], "unapplied")
        partial_payment = next(payment for payment in payload["data"]["payments"] if payment["id"] == 75)
        self.assertEqual(partial_payment["applied_amount_cents"], 18500)
        self.assertEqual(partial_payment["unapplied_amount_cents"], 21500)

    def test_editor_returns_applications_and_open_invoices(self) -> None:
        response = self.client.get("/api/payments/75/editor")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]

        self.assertEqual(payload["payment"]["reference_number"], "ACH-9920")
        self.assertEqual(len(payload["applications"]), 1)
        self.assertEqual(payload["applications"][0]["invoice_number"], "INV-2026-024")
        self.assertEqual(len(payload["open_invoices"]), 1)
        self.assertEqual(payload["open_invoices"][0]["invoice_number"], "INV-2026-024")
        self.assertEqual(payload["open_invoices"][0]["available_to_apply_cents"], 42500)

    def test_create_update_and_replace_payment_applications(self) -> None:
        create_response = self.client.post(
            "/api/payments",
            json={
                "customer_id": 24,
                "payment_date": "2026-05-31",
                "payment_type": "payment",
                "reference_number": "WIRE-303",
                "amount_cents": 15000,
                "notes": "Applied after invoice review.",
            },
        )

        self.assertEqual(create_response.status_code, 200)
        created_payment = create_response.json()["data"]["payment"]
        self.assertEqual(created_payment["customer_name"], "Horizon Ventures")
        self.assertEqual(created_payment["application_status"], "unapplied")

        update_response = self.client.put(
            f"/api/payments/{created_payment['id']}",
            json={
                "customer_id": 24,
                "payment_date": "2026-05-31",
                "payment_type": "advance",
                "reference_number": "WIRE-303A",
                "amount_cents": 16000,
                "notes": "Held as advance until owner confirmation.",
            },
        )

        self.assertEqual(update_response.status_code, 200)
        updated_payment = update_response.json()["data"]["payment"]
        self.assertEqual(updated_payment["payment_type"], "advance")
        self.assertEqual(updated_payment["reference_number"], "WIRE-303A")

        applications_response = self.client.post(
            f"/api/payments/{created_payment['id']}/applications",
            json={
                "applications": [
                    {
                        "invoice_id": 205,
                        "applied_amount_cents": 12600,
                    }
                ]
            },
        )

        self.assertEqual(applications_response.status_code, 200)
        editor_payload = applications_response.json()["data"]
        self.assertEqual(editor_payload["payment"]["application_status"], "partially_applied")
        self.assertEqual(editor_payload["payment"]["applied_amount_cents"], 12600)
        self.assertEqual(editor_payload["payment"]["unapplied_amount_cents"], 3400)
        self.assertEqual(editor_payload["applications"][0]["invoice_number"], "INV-2026-019")
        self.assertEqual(editor_payload["open_invoices"][0]["status"], "paid")


if __name__ == "__main__":
    unittest.main()