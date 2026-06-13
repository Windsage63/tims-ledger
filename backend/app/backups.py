from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
import sqlite3
import tempfile
import zipfile

from pydantic import BaseModel, ConfigDict, field_validator

from .config import Settings


BACKUP_PREFIX = "Tims-Ledger-Backup-"
SAFETY_BACKUP_PREFIX = "Tims-Ledger-Safety-Backup-"
BACKUP_SUFFIX = ".zip"


class BackupRestoreWrite(BaseModel):
    file_name: str

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("file_name")
    @classmethod
    def require_safe_zip_name(cls, value: str) -> str:
        if not value:
            raise ValueError("Backup file is required.")
        if Path(value).name != value or not value.endswith(BACKUP_SUFFIX):
            raise ValueError("Backup file is invalid.")
        return value


@dataclass(frozen=True)
class BackupPaths:
    backups_dir: Path
    safety_dir: Path
    invoices_dir: Path


def backup_paths(settings: Settings) -> BackupPaths:
    backups_dir = settings.data_dir / "backups"
    return BackupPaths(
        backups_dir=backups_dir,
        safety_dir=backups_dir / "safety",
        invoices_dir=settings.data_dir / "invoices",
    )


def timestamp_label() -> str:
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")


def backup_file_payload(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {
        "file_name": path.name,
        "size_bytes": stat.st_size,
        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def list_backup_files(settings: Settings) -> list[dict[str, object]]:
    paths = backup_paths(settings)
    paths.backups_dir.mkdir(parents=True, exist_ok=True)
    backups = [
        path
        for path in paths.backups_dir.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}")
        if path.is_file()
    ]
    return [backup_file_payload(path) for path in sorted(backups, key=lambda path: path.stat().st_mtime, reverse=True)]


def copy_database_snapshot(source_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source_path, timeout=5) as source:
        source.execute("PRAGMA wal_checkpoint(FULL)").fetchall()
    shutil.copy2(source_path, target_path)


def write_backup_zip(settings: Settings, output_dir: Path, *, safety: bool = False) -> dict[str, object]:
    paths = backup_paths(settings)
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = SAFETY_BACKUP_PREFIX if safety else BACKUP_PREFIX
    backup_path = output_dir / f"{prefix}{timestamp_label()}{BACKUP_SUFFIX}"

    with tempfile.TemporaryDirectory(dir=str(settings.data_dir)) as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        database_snapshot = temp_dir / settings.database_path.name
        copy_database_snapshot(settings.database_path, database_snapshot)

        with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(database_snapshot, arcname=settings.database_path.name)
            if paths.invoices_dir.exists():
                for invoice_file in paths.invoices_dir.rglob("*"):
                    if invoice_file.is_file():
                        archive.write(invoice_file, arcname=str(invoice_file.relative_to(settings.data_dir)))

    return backup_file_payload(backup_path)


def create_backup(settings: Settings) -> dict[str, object]:
    return write_backup_zip(settings, backup_paths(settings).backups_dir)


def create_safety_backup(settings: Settings) -> dict[str, object]:
    return write_backup_zip(settings, backup_paths(settings).safety_dir, safety=True)


def ensure_safe_archive_member(member_name: str) -> Path:
    member_path = Path(member_name)
    if member_path.is_absolute() or ".." in member_path.parts:
        raise ValueError("Backup archive contains an unsafe path.")
    return member_path


def restore_backup(settings: Settings, file_name: str) -> dict[str, object]:
    paths = backup_paths(settings)
    backup_path = paths.backups_dir / file_name
    if backup_path.parent != paths.backups_dir or not backup_path.exists() or not backup_path.is_file():
        raise ValueError("Backup file not found.")

    safety_backup = create_safety_backup(settings)

    with tempfile.TemporaryDirectory(dir=str(settings.data_dir)) as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        restore_dir = temp_dir / "restore"
        restore_dir.mkdir()

        with zipfile.ZipFile(backup_path, "r") as archive:
            for member in archive.namelist():
                ensure_safe_archive_member(member)
            archive.extractall(restore_dir)

        restored_database = restore_dir / settings.database_path.name
        if not restored_database.exists() or not restored_database.is_file():
            raise ValueError("Backup archive is missing the database.")

        settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(restored_database, settings.database_path)

        restored_invoices = restore_dir / "invoices"
        if paths.invoices_dir.exists():
            shutil.rmtree(paths.invoices_dir)
        if restored_invoices.exists():
            shutil.copytree(restored_invoices, paths.invoices_dir)

    return {
        "restored_backup": backup_file_payload(backup_path),
        "safety_backup": safety_backup,
    }
