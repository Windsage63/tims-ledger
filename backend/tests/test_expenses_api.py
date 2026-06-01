from __future__ import annotations

import unittest

from tests.fixtures.full_ledger_db import load_full_ledger_db
from tests.support.api_test_case import ApiTestCase


class ExpensesApiTests(ApiTestCase):
    fixture_loader = load_full_ledger_db

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

    def test_rejects_invalid_entry_date(self) -> None:
        response = self.client.post(
            "/api/expenses",
            json={
                "entry_date": "not-a-date",
                "project_id": 36,
                "vendor": "Campus Copy",
                "description": "Concept boards for client review.",
                "quantity": 1.5,
                "unit_cost_cents": 1234,
                "category": "Supplies",
                "is_billable": True,
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("valid ISO date", response.text)

    def test_cannot_update_expense_on_printed_invoice(self) -> None:
        response = self.client.put(
            "/api/expenses/813",
            json={
                "entry_date": "2026-05-21",
                "project_id": 35,
                "vendor": "Updated Vendor",
                "description": "Blocked after issue",
                "quantity": 3,
                "unit_cost_cents": 4200,
                "category": "Equipment",
                "is_billable": True,
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Expenses on printed invoices are read-only.")


if __name__ == "__main__":
    unittest.main()