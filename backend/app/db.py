from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from .config import Settings


SCHEMA_MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class DatabaseStatus:
    database_path: str
    applied_migrations: list[str]
    pending_migrations: list[str]
    table_count: int
    view_count: int


def connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensure_database_parent(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)


def list_migration_files(migrations_dir: Path) -> list[Path]:
    return sorted(path for path in migrations_dir.glob("*.sql") if path.is_file())


def ensure_schema_migrations_table(connection: sqlite3.Connection) -> None:
    connection.execute(SCHEMA_MIGRATIONS_SQL)
    connection.commit()


def fetch_applied_migrations(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT filename FROM schema_migrations ORDER BY filename"
    ).fetchall()
    return [row["filename"] for row in rows]


def apply_pending_migrations(settings: Settings) -> list[str]:
    ensure_database_parent(settings.database_path)

    with connect(settings.database_path) as connection:
        ensure_schema_migrations_table(connection)
        applied = set(fetch_applied_migrations(connection))
        applied_now: list[str] = []

        for migration_path in list_migration_files(settings.migrations_dir):
            if migration_path.name in applied:
                continue

            sql = migration_path.read_text(encoding="utf-8")
            connection.executescript(sql)
            connection.execute(
                "INSERT INTO schema_migrations (filename, applied_at) VALUES (?, ?)",
                (migration_path.name, datetime.now(timezone.utc).isoformat()),
            )
            connection.commit()
            applied_now.append(migration_path.name)

        return applied_now


def get_database_status(settings: Settings) -> DatabaseStatus:
    ensure_database_parent(settings.database_path)

    with connect(settings.database_path) as connection:
        ensure_schema_migrations_table(connection)
        applied_migrations = fetch_applied_migrations(connection)
        pending_migrations = [
            path.name
            for path in list_migration_files(settings.migrations_dir)
            if path.name not in set(applied_migrations)
        ]
        table_count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
        view_count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'view'"
        ).fetchone()[0]

    return DatabaseStatus(
        database_path=str(settings.database_path),
        applied_migrations=applied_migrations,
        pending_migrations=pending_migrations,
        table_count=table_count,
        view_count=view_count,
    )