from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    data_dir: Path
    database_path: Path
    migrations_dir: Path
    skip_startup_migrations: bool


def load_settings() -> Settings:
    repo_root = Path(__file__).resolve().parents[2]
    data_dir = Path(os.getenv("TIMS_LEDGER_DATA_DIR", str(repo_root / "app-data")))
    database_path = Path(os.getenv("TIMS_LEDGER_DB_PATH", str(data_dir / "tims-ledger.db")))
    migrations_dir = Path(os.getenv("TIMS_LEDGER_MIGRATIONS_DIR", str(repo_root / "migrations")))
    skip_startup_migrations = os.getenv("TIMS_LEDGER_SKIP_STARTUP_MIGRATIONS", "0") == "1"

    return Settings(
        repo_root=repo_root,
        data_dir=data_dir,
        database_path=database_path,
        migrations_dir=migrations_dir,
        skip_startup_migrations=skip_startup_migrations,
    )
