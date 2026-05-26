from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import OcrJobStatus


class ReceiptCreate(BaseModel):
    path: str = Field(min_length=1)
    file_type: str = Field(default="receipt", max_length=50)
    mime_type: str | None = Field(default=None, max_length=100)

    @field_validator("path")
    @classmethod
    def require_existing_path(cls, value: str) -> str:
        if not Path(value).expanduser().is_file():
            raise ValueError("Receipt path must point to an existing file.")
        return value


class FileRead(BaseModel):
    id: int
    file_type: str
    original_name: str
    storage_path: str
    mime_type: str | None
    sha256: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OcrJobRead(BaseModel):
    id: int
    file_id: int
    status: OcrJobStatus
    provider: str | None
    extracted_json: dict[str, Any] | None
    confidence: Decimal | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReceiptCreateRead(BaseModel):
    file: FileRead
    ocr_job: OcrJobRead


class OcrSuggestionsUpdate(BaseModel):
    provider: str = Field(default="manual", max_length=120)
    extracted_json: dict[str, Any]
    confidence: Decimal | None = Field(default=None, ge=0, le=1, decimal_places=4)


class OcrReviewCreate(BaseModel):
    reviewed_by: str | None = Field(default=None, max_length=120)
    project_id: int = Field(gt=0)
    date: str
    vendor: str | None = Field(default=None, max_length=200)
    description: str = Field(min_length=1)
    qty: Decimal = Field(default=Decimal("1.00"), gt=0, decimal_places=2)
    unit_cost: Decimal = Field(ge=0, decimal_places=2)
    total: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    category_id: int | None = Field(default=None, gt=0)
    billable: bool = True
    reimbursable: bool = True
    paid_by: str | None = Field(default=None, max_length=120)
    payment_method: str | None = Field(default=None, max_length=120)
