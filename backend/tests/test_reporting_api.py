from __future__ import annotations

from io import BytesIO
import unittest
from zipfile import ZipFile

from tests.fixtures.full_ledger_db import load_full_ledger_db
from tests.support.api_test_case import ApiTestCase


class ReportingApiTests(ApiTestCase):
    fixture_loader = load_full_ledger_db

    def test_accounts_receivable_report_returns_balances_and_statement(self) -> None:
        response = self.client.get("/api/reports/accounts-receivable?customer_id=19")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["meta"]["screen"], "accounts_receivable")
        self.assertEqual(payload["data"]["summary"]["total_open_ar_cents"], 83875)
        self.assertEqual(payload["data"]["summary"]["total_unapplied_credit_cents"], 174100)
        self.assertEqual(payload["data"]["summary"]["net_receivables_cents"], -90225)
        self.assertEqual(payload["data"]["selected_customer_id"], 19)
        self.assertEqual(payload["data"]["statement"]["customer"]["customer_name"], "Nexa Synergy Group")
        self.assertTrue(any(invoice["invoice_number"] == "INV-2026-014" for invoice in payload["data"]["statement"]["invoices"]))
        self.assertEqual(payload["data"]["statement"]["unapplied_payments"][0]["id"], 72)
        self.assertEqual(payload["data"]["audit_export_path"], "/api/exports/audit.xlsx")

    def test_audit_export_returns_xlsx_workbook(self) -> None:
        response = self.client.get("/api/exports/audit.xlsx")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["content-type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(response.content.startswith(b"PK"))

        with ZipFile(BytesIO(response.content)) as workbook_zip:
            names = set(workbook_zip.namelist())
            workbook_xml = workbook_zip.read("xl/workbook.xml")

        self.assertIn("[Content_Types].xml", names)
        self.assertIn("xl/workbook.xml", names)
        self.assertIn("xl/worksheets/sheet1.xml", names)
        self.assertIn(b"CustomerBalances", workbook_xml)
        self.assertIn(b"UnappliedPayments", workbook_xml)


if __name__ == "__main__":
    unittest.main()