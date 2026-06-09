from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys

import uvicorn

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import Settings
from app.db import apply_pending_migrations, connect
from app.main import create_app
from tests.fixtures.full_ledger_db import load_full_ledger_db


def build_settings() -> Settings:
    data_dir = Path(os.environ["WINDS_LEDGER_E2E_DATA_DIR"])
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        repo_root=REPO_ROOT,
        data_dir=data_dir,
        database_path=data_dir / "winds-ledger.db",
        migrations_dir=REPO_ROOT / "migrations",
        skip_startup_migrations=True,
    )


def main() -> None:
    settings = build_settings()
    apply_pending_migrations(settings)
    with connect(settings.database_path) as connection:
        load_full_ledger_db(connection)

    app = create_app(settings)
    uvicorn.run(
        app,
        host=os.getenv("WINDS_LEDGER_E2E_HOST", "127.0.0.1"),
        port=int(os.getenv("WINDS_LEDGER_E2E_PORT", "4173")),
        log_level="warning",
    )


if __name__ == "__main__":
    main()