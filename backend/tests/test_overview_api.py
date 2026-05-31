from __future__ import annotations

import unittest

from tests.fixtures.full_ledger_db import load_full_ledger_db
from tests.support.api_test_case import ApiTestCase


class OverviewApiTests(ApiTestCase):
    fixture_loader = load_full_ledger_db

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