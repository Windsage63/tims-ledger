from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app


class OverviewApiTests(unittest.TestCase):
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

    def test_bootstrap_returns_real_dashboard_summary(self) -> None:
        response = self.client.get("/api/overview/bootstrap")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["meta"]["screen"], "overview")
        summary = payload["data"]["summary"]
        self.assertEqual(summary["customers_count"], 6)
        self.assertEqual(summary["projects_count"], 6)
        self.assertEqual(summary["time_entries_count"], 7)
        self.assertEqual(summary["expenses_count"], 7)
        self.assertEqual(summary["invoices_count"], 5)
        self.assertEqual(summary["issued_invoices_count"], 4)
        self.assertEqual(summary["draft_invoices_count"], 1)
        self.assertEqual(summary["payments_count"], 6)
        self.assertEqual(summary["open_receivables_cents"], 83875)
        self.assertEqual(summary["unapplied_receipts_cents"], 174100)
        self.assertEqual(summary["unbilled_time_cents"], 66100)
        self.assertEqual(summary["unbilled_expenses_cents"], 24262)
        self.assertEqual(summary["unbilled_work_cents"], 90362)
        self.assertIn("winds-ledger-test.db", payload["data"]["system"]["database_path"])
        self.assertEqual(payload["data"]["system"]["pending_migrations_count"], 0)


if __name__ == "__main__":
    unittest.main()