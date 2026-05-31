from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app


class CustomerApiTests(unittest.TestCase):
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

    def test_bootstrap_returns_seeded_customers(self) -> None:
        response = self.client.get("/api/customers/bootstrap")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        customers = payload["data"]["customers"]

        self.assertEqual(len(customers), 6)
        self.assertEqual(customers[0]["customer_name"], "Acme Corp.")
        self.assertEqual(payload["meta"]["screen"], "customers")

    def test_create_and_update_customer(self) -> None:
        create_response = self.client.post(
            "/api/customers",
            json={
                "customer_name": "River Birch Engineering",
                "street_address": "110 Harbor Way",
                "city": "Tacoma",
                "state": "wa",
                "zip": "98402",
                "contact_name": "Mara Holt",
                "email": "mholt@riverbirch.example",
                "phone": "555-0147",
                "notes": "Created by API test",
            },
        )

        self.assertEqual(create_response.status_code, 200)
        created_customer = create_response.json()["data"]["customer"]
        self.assertEqual(created_customer["state"], "WA")
        self.assertEqual(created_customer["open_ar_cents"], 0)

        update_response = self.client.put(
            f"/api/customers/{created_customer['id']}",
            json={
                "customer_name": "River Birch Engineering",
                "street_address": "110 Harbor Way",
                "city": "Tacoma",
                "state": "WA",
                "zip": "98402",
                "contact_name": "Mara Holt",
                "email": "billing@riverbirch.example",
                "phone": "555-0147",
                "notes": "Updated by API test",
            },
        )

        self.assertEqual(update_response.status_code, 200)
        updated_customer = update_response.json()["data"]["customer"]
        self.assertEqual(updated_customer["email"], "billing@riverbirch.example")
        self.assertEqual(updated_customer["notes"], "Updated by API test")


if __name__ == "__main__":
    unittest.main()