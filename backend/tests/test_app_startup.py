from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


class AppStartupTests(unittest.TestCase):
    def test_startup_applies_migrations_without_loading_fixture_data(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            settings = Settings(
                repo_root=repo_root,
                data_dir=temp_path,
                database_path=temp_path / "winds-ledger-startup.db",
                migrations_dir=repo_root / "migrations",
                skip_startup_migrations=False,
            )

            with TestClient(create_app(settings)) as client:
                status_response = client.get("/api/system/status")
                customers_response = client.get("/api/customers/bootstrap")
                self.assertEqual(status_response.status_code, 200)
                status_payload = status_response.json()
                self.assertEqual(status_payload["pending_migrations"], [])
                self.assertGreater(status_payload["table_count"], 0)
                self.assertTrue(Path(status_payload["database_path"]).exists())

                self.assertEqual(customers_response.status_code, 200)
                self.assertEqual(customers_response.json()["data"]["customers"], [])


if __name__ == "__main__":
    unittest.main()
