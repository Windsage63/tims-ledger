import json
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.engine import make_url

from app.core.config import settings


def create_backup() -> dict:
    created_at = datetime.now(UTC)
    backup_dir = Path("app-data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"windsage-ledger-backup-{created_at:%Y%m%d-%H%M%S}.zip"

    database_path = _database_path()
    file_storage = Path(settings.file_storage)
    included_files = []

    with ZipFile(backup_path, mode="w", compression=ZIP_DEFLATED) as archive:
        included_database = database_path is not None and database_path.exists()
        if included_database:
            archive.write(database_path, "database/windsage-ledger.sqlite3")

        if file_storage.exists():
            for path in file_storage.rglob("*"):
                if not path.is_file() or "backups" in path.parts:
                    continue
                relative_path = path.relative_to(file_storage)
                archive.write(path, f"files/{relative_path.as_posix()}")
                included_files.append(str(relative_path))

        manifest = {
            "created_at": created_at.isoformat(),
            "database_url": settings.database_url,
            "included_database": included_database,
            "included_files": included_files,
        }
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))

    return {
        "path": str(backup_path),
        "created_at": created_at,
        "included_database": included_database,
        "included_file_count": len(included_files),
    }


def _database_path() -> Path | None:
    url = make_url(settings.database_url)
    if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
        return None
    return Path(url.database)
