from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class WorkbookPreviewRequest(BaseModel):
    path: str = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def require_excel_file(cls, value: str) -> str:
        suffix = Path(value).suffix.lower()
        if suffix not in {".xlsx", ".xlsm"}:
            raise ValueError("Workbook path must point to an .xlsx or .xlsm file.")
        return value


class WorkbookSheetPreview(BaseModel):
    name: str
    max_row: int
    max_column: int
    header_row: int | None
    headers: list[str]
    mapping_hint: str | None


class WorkbookPreviewRead(BaseModel):
    path: str
    sheets: list[WorkbookSheetPreview]
