from __future__ import annotations

import unittest

from tests.fixtures.customers_db import load_customers_db
from tests.support.api_test_case import ApiTestCase


class CustomerApiTests(ApiTestCase):
    fixture_loader = load_customers_db

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