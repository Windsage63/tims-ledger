from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app


class TimeApiTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()