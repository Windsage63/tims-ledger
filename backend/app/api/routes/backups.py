from fastapi import APIRouter

from app.schemas.backups import BackupCreateRead
from app.services.backups import create_backup

router = APIRouter(prefix="/backups", tags=["backups"])


@router.post("", response_model=BackupCreateRead, status_code=201)
def create_backup_route() -> dict:
    return create_backup()
