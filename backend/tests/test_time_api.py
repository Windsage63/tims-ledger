from __future__ import annotations

import unittest

from tests.fixtures.full_ledger_db import load_full_ledger_db
from tests.support.api_test_case import ApiTestCase


class TimeApiTests(ApiTestCase):
    fixture_loader = load_full_ledger_db

    def test_bootstrap_returns_seeded_entries_and_lookup_data(self) -> None:
        response = self.client.get("/api/time/bootstrap")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["meta"]["screen"], "time")
        self.assertEqual(len(payload["data"]["entries"]), 7)
        self.assertEqual(len(payload["data"]["projects"]), 6)
        self.assertEqual(len(payload["data"]["customers"]), 6)
        invoiced_entry = next(entry for entry in payload["data"]["entries"] if entry["id"] == 403)
        self.assertEqual(invoiced_entry["invoice_number"], "INV-2026-014")
        project_35_rates = payload["data"]["rates_by_project"]["35"]
        self.assertTrue(any(rate["rate_code"] == "NB" and rate["rate_cents"] == 0 for rate in project_35_rates))

    def test_bootstrap_year_filter_limits_entries(self) -> None:
        response = self.client.get("/api/time/bootstrap?year=2025")

        self.assertEqual(response.status_code, 200)
        entries = response.json()["data"]["entries"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["id"], 406)

    def test_create_and_update_time_entry(self) -> None:
        create_response = self.client.post(
            "/api/time-entries",
            json={
                "entry_date": "2026-05-31",
                "project_id": 35,
                "description": "Retention basin analysis",
                "minutes": 90,
                "rate_code": "SITE",
            },
        )

        self.assertEqual(create_response.status_code, 200)
        created_entry = create_response.json()["data"]["entry"]
        self.assertEqual(created_entry["customer_name"], "Horizon Ventures")
        self.assertEqual(created_entry["project_number"], "0528")
        self.assertEqual(created_entry["rate_cents"], 11000)
        self.assertEqual(created_entry["line_total_cents"], 16500)

        update_response = self.client.put(
            f"/api/time-entries/{created_entry['id']}",
            json={
                "entry_date": "2026-05-31",
                "project_id": 35,
                "description": "Retention basin analysis internal review",
                "minutes": 75,
                "rate_code": "NB",
            },
        )

        self.assertEqual(update_response.status_code, 200)
        updated_entry = update_response.json()["data"]["entry"]
        self.assertEqual(updated_entry["rate_code"], "NB")
        self.assertEqual(updated_entry["rate_cents"], 0)
        self.assertEqual(updated_entry["line_total_cents"], 0)
        self.assertEqual(updated_entry["invoice_number"], None)

    def test_rejects_invalid_entry_date(self) -> None:
        response = self.client.post(
            "/api/time-entries",
            json={
                "entry_date": "not-a-date",
                "project_id": 35,
                "description": "Retention basin analysis",
                "minutes": 90,
                "rate_code": "SITE",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("valid ISO date", response.text)

    def test_cannot_update_time_entry_on_issued_invoice(self) -> None:
        before_response = self.client.get("/api/invoices/201/editor")
        before_total = before_response.json()["data"]["summary"]["invoice_total_cents"]

        response = self.client.put(
            "/api/time-entries/403",
            json={
                "entry_date": "2026-05-22",
                "project_id": 34,
                "description": "Blocked after issue",
                "minutes": 255,
                "rate_code": "OT",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Time entries on issued invoices are read-only.")

        after_response = self.client.get("/api/invoices/201/editor")
        after_total = after_response.json()["data"]["summary"]["invoice_total_cents"]
        self.assertEqual(after_total, before_total)


if __name__ == "__main__":
    unittest.main()