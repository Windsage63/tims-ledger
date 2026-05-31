from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

from fastapi.testclient import TestClient

from app.config import Settings
from app.db import apply_pending_migrations, connect
from app.main import create_app


FixtureLoader = Callable[[object], int | None]


class DatabaseHarness:
    def __init__(self, fixture_loader: FixtureLoader | None = None):
        self.fixture_loader = fixture_loader
        self.temp_dir: TemporaryDirectory[str] | None = None
        self.settings: Settings | None = None
        self.client_context: TestClient | None = None
        self.client = None

    def start(self):
        repo_root = Path(__file__).resolve().parents[3]
        self.temp_dir = TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.settings = Settings(
            repo_root=repo_root,
            data_dir=temp_path,
            database_path=temp_path / "winds-ledger-test.db",
            migrations_dir=repo_root / "migrations",
            skip_startup_migrations=True,
        )

        apply_pending_migrations(self.settings)

        if self.fixture_loader is not None:
            with connect(self.settings.database_path) as connection:
                self.fixture_loader(connection)

        self.client_context = TestClient(create_app(self.settings))
        self.client = self.client_context.__enter__()
        return self.client

    def close(self) -> None:
        if self.client_context is not None:
            self.client_context.__exit__(None, None, None)
        self.client = None
        self.client_context = None
        self.settings = None

        if self.temp_dir is not None:
            try:
                self.temp_dir.cleanup()
            except PermissionError:
                pass
            self.temp_dir = None
