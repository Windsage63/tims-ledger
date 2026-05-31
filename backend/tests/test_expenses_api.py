from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app


class ExpensesApiTests(unittest.TestCase):
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

    def test_bootstrap_returns_seeded_expenses_and_lookup_data(self) -> None:
        response = self.client.get("/api/expenses/bootstrap")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["meta"]["screen"], "expenses")
        self.assertEqual(len(payload["data"]["expenses"]), 7)
        self.assertEqual(len(payload["data"]["projects"]), 6)
        self.assertEqual(len(payload["data"]["customers"]), 6)
        self.assertEqual(payload["data"]["categories"], [
            "Equipment",
            "Meals",
            "Mileage",
            "Permits",
            "Printing",
            "Records",
            "Supplies",
            "Travel",
        ])
        invoiced_expense = next(expense for expense in payload["data"]["expenses"] if expense["id"] == 813)
        self.assertEqual(invoiced_expense["invoice_number"], "INV-2026-019")

    def test_bootstrap_year_filter_limits_expenses(self) -> None:
        response = self.client.get("/api/expenses/bootstrap?year=2025")

        self.assertEqual(response.status_code, 200)
        expenses = response.json()["data"]["expenses"]
        self.assertEqual(len(expenses), 1)
        self.assertEqual(expenses[0]["id"], 817)

    def test_create_and_update_expense(self) -> None:
        create_response = self.client.post(
            "/api/expenses",
            json={
                "entry_date": "2026-05-31",
                "project_id": 36,
                "vendor": "Campus Copy",
                "description": "Concept boards for client review.",
                "quantity": 1.5,
                "unit_cost_cents": 1234,
                "category": "Supplies",
                "is_billable": True,
            },
        )

        self.assertEqual(create_response.status_code, 200)
        created_expense = create_response.json()["data"]["expense"]
        self.assertEqual(created_expense["customer_name"], "Aura Design Studio")
        self.assertEqual(created_expense["project_number"], "0611")
        self.assertEqual(created_expense["line_total_cents"], 1851)
        self.assertEqual(created_expense["invoice_number"], None)

        update_response = self.client.put(
            f"/api/expenses/{created_expense['id']}",
            json={
                "entry_date": "2026-05-31",
                "project_id": 35,
                "vendor": "Campus Copy",
                "description": "Internal concept boards retained for archive.",
                "quantity": 2,
                "unit_cost_cents": 1200,
                "category": "Travel",
                "is_billable": False,
            },
        )

        self.assertEqual(update_response.status_code, 200)
        updated_expense = update_response.json()["data"]["expense"]
        self.assertEqual(updated_expense["customer_name"], "Horizon Ventures")
        self.assertEqual(updated_expense["project_number"], "0528")
        self.assertEqual(updated_expense["category"], "Travel")
        self.assertFalse(updated_expense["is_billable"])
        self.assertEqual(updated_expense["line_total_cents"], 2400)


if __name__ == "__main__":
    unittest.main()