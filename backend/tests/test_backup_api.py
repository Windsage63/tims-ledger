from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient


def test_create_backup_zip_contains_manifest(api_client: TestClient) -> None:
    response = api_client.post("/api/backups")

    assert response.status_code == 201
    body = response.json()
    backup_path = Path(body["path"])
    assert backup_path.exists()
    assert backup_path.suffix == ".zip"

    with ZipFile(backup_path) as archive:
        assert "manifest.json" in archive.namelist()
