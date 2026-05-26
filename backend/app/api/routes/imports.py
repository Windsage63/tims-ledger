from fastapi import APIRouter

from app.api.errors import ConflictError, NotFoundError
from app.schemas.imports import WorkbookPreviewRead, WorkbookPreviewRequest
from app.services.imports import preview_workbook

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/workbook/preview", response_model=WorkbookPreviewRead)
def preview_workbook_route(payload: WorkbookPreviewRequest) -> dict:
    try:
        return preview_workbook(payload.path)
    except FileNotFoundError as exc:
        raise NotFoundError(str(exc)) from exc
    except ValueError as exc:
        raise ConflictError(str(exc)) from exc
