from __future__ import annotations

import unittest

from tests.fixtures.projects_db import load_projects_db
from tests.support.api_test_case import ApiTestCase


class ProjectApiTests(ApiTestCase):
    fixture_loader = load_projects_db

    def test_bootstrap_returns_seeded_projects_and_lookup(self) -> None:
        response = self.client.get("/api/projects/bootstrap")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["meta"]["screen"], "projects")
        self.assertEqual(len(payload["data"]["projects"]), 6)
        self.assertEqual(len(payload["data"]["customers"]), 6)
        self.assertEqual(payload["data"]["projects"][0]["project_number"], "0495")
        self.assertEqual(payload["data"]["projects"][0]["rates"][0]["rate_code"], "ST")

    def test_create_and_update_project(self) -> None:
        create_response = self.client.post(
            "/api/projects",
            json={
                "project_number": "0702",
                "customer_id": 12,
                "description": "Floodplain analysis",
                "default_rate_cents": 13200,
                "rates": [
                    {"rate_code": "ST", "rate_cents": 13200, "is_builtin": True, "sort_order": 1},
                    {"rate_code": "OT", "rate_cents": 19800, "is_builtin": True, "sort_order": 2},
                    {"rate_code": "TT", "rate_cents": 6600, "is_builtin": True, "sort_order": 3},
                    {"rate_code": "FIELD", "rate_cents": 15500, "is_builtin": False, "sort_order": 10},
                ],
            },
        )

        self.assertEqual(create_response.status_code, 200)
        created_project = create_response.json()["data"]["project"]
        self.assertEqual(created_project["customer_name"], "Acme Corp.")
        self.assertEqual(created_project["rates"][0]["rate_cents"], 13200)
        self.assertEqual(created_project["rates"][3]["rate_code"], "FIELD")

        update_response = self.client.put(
            f"/api/projects/{created_project['id']}",
            json={
                "project_number": "0702",
                "customer_id": 19,
                "description": "Floodplain analysis revised",
                "default_rate_cents": 14000,
                "rates": [
                    {"rate_code": "ST", "rate_cents": 14000, "is_builtin": True, "sort_order": 1},
                    {"rate_code": "OT", "rate_cents": 21000, "is_builtin": True, "sort_order": 2},
                    {"rate_code": "TT", "rate_cents": 7000, "is_builtin": True, "sort_order": 3},
                    {"rate_code": "FIELD", "rate_cents": 16500, "is_builtin": False, "sort_order": 10},
                    {"rate_code": "QC", "rate_cents": 9000, "is_builtin": False, "sort_order": 11},
                ],
            },
        )

        self.assertEqual(update_response.status_code, 200)
        updated_project = update_response.json()["data"]["project"]
        self.assertEqual(updated_project["customer_name"], "Nexa Synergy Group")
        self.assertEqual(updated_project["default_rate_cents"], 14000)
        self.assertEqual(updated_project["rates"][1]["rate_cents"], 21000)
        self.assertEqual(len(updated_project["rates"]), 5)

    def test_duplicate_project_number_returns_conflict(self) -> None:
        response = self.client.post(
            "/api/projects",
            json={
                "project_number": "0526",
                "customer_id": 12,
                "description": "Duplicate number check",
                "default_rate_cents": 12000,
                "rates": [
                    {"rate_code": "ST", "rate_cents": 12000, "is_builtin": True, "sort_order": 1},
                    {"rate_code": "OT", "rate_cents": 18000, "is_builtin": True, "sort_order": 2},
                    {"rate_code": "TT", "rate_cents": 6000, "is_builtin": True, "sort_order": 3},
                ],
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "Project number must be unique.")

    def test_invalid_customer_returns_clear_validation_error(self) -> None:
        response = self.client.post(
            "/api/projects",
            json={
                "project_number": "0799",
                "customer_id": 999999,
                "description": "Invalid customer check",
                "default_rate_cents": 12000,
                "rates": [
                    {"rate_code": "ST", "rate_cents": 12000, "is_builtin": True, "sort_order": 1},
                    {"rate_code": "OT", "rate_cents": 18000, "is_builtin": True, "sort_order": 2},
                    {"rate_code": "TT", "rate_cents": 6000, "is_builtin": True, "sort_order": 3},
                ],
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Customer not found.")


if __name__ == "__main__":
    unittest.main()