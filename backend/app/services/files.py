import hashlib
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import File


def store_local_file(
    session: Session,
    *,
    path: str,
    file_type: str,
    mime_type: str | None = None,
) -> File:
    source = Path(path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"File was not found: {source}")

    sha256 = _sha256(source)
    storage_dir = Path(settings.file_storage) / file_type
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_name = f"{sha256}{source.suffix.lower()}"
    destination = storage_dir / storage_name
    if not destination.exists():
        shutil.copy2(source, destination)

    file = File(
        file_type=file_type,
        original_name=source.name,
        storage_path=str(destination),
        mime_type=mime_type,
        sha256=sha256,
    )
    session.add(file)
    session.flush()
    return file


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
