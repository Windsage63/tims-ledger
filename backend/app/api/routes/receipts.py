from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.errors import ConflictError, NotFoundError
from app.db.session import get_session
from app.models import BillingStatus, Expense, ExpenseCategory, File, OcrJob, OcrJobStatus, Project
from app.schemas.expenses import ExpenseRead
from app.schemas.receipts import (
    OcrJobRead,
    OcrReviewCreate,
    OcrSuggestionsUpdate,
    ReceiptCreate,
    ReceiptCreateRead,
)
from app.services import money
from app.services.files import store_local_file

router = APIRouter(prefix="/receipts", tags=["receipts"])
ocr_router = APIRouter(prefix="/ocr-jobs", tags=["ocr jobs"])


@router.post("", response_model=ReceiptCreateRead, status_code=201)
def create_receipt(
    payload: ReceiptCreate,
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    try:
        file = store_local_file(
            session,
            path=payload.path,
            file_type=payload.file_type,
            mime_type=payload.mime_type,
        )
    except FileNotFoundError as exc:
        raise NotFoundError(str(exc)) from exc

    job = OcrJob(file_id=file.id, status=OcrJobStatus.PENDING.value)
    session.add(job)
    session.commit()
    session.refresh(file)
    session.refresh(job)
    return {"file": file, "ocr_job": job}


@ocr_router.get("/{job_id}", response_model=OcrJobRead)
def get_ocr_job(
    job_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> OcrJob:
    return _get_job(session, job_id)


@ocr_router.patch("/{job_id}/suggestions", response_model=OcrJobRead)
def update_ocr_suggestions(
    job_id: int,
    payload: OcrSuggestionsUpdate,
    session: Annotated[Session, Depends(get_session)],
) -> OcrJob:
    job = _get_job(session, job_id)
    if job.status == OcrJobStatus.APPROVED.value:
        raise ConflictError("Approved OCR jobs cannot be changed.")

    job.provider = payload.provider
    job.extracted_json = payload.extracted_json
    job.confidence = payload.confidence
    job.status = OcrJobStatus.NEEDS_REVIEW.value
    session.commit()
    session.refresh(job)
    return job


@ocr_router.post("/{job_id}/review", response_model=ExpenseRead)
def approve_ocr_job(
    job_id: int,
    payload: OcrReviewCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Expense:
    job = _get_job(session, job_id)
    if job.status == OcrJobStatus.APPROVED.value:
        raise ConflictError("OCR job has already been approved.")
    file = _get_file(session, job.file_id)
    project = _get_project(session, payload.project_id)
    _ensure_category_exists(session, payload.category_id)

    expense = Expense(
        date=date.fromisoformat(payload.date),
        project_id=project.id,
        customer_id=project.customer_id,
        vendor=payload.vendor,
        description=payload.description,
        qty=payload.qty,
        unit_cost=money(payload.unit_cost),
        total=money(
            payload.total if payload.total is not None else payload.qty * payload.unit_cost,
        ),
        category_id=payload.category_id,
        billable=payload.billable,
        reimbursable=payload.reimbursable,
        paid_by=payload.paid_by,
        payment_method=payload.payment_method,
        reimbursement_status=(
            BillingStatus.UNBILLED.value
            if payload.billable and payload.reimbursable
            else BillingStatus.NON_BILLABLE.value
        ),
        receipt_file_id=file.id,
    )
    session.add(expense)
    job.status = OcrJobStatus.APPROVED.value
    job.reviewed_by = payload.reviewed_by
    job.reviewed_at = datetime.now(UTC)
    session.commit()
    session.refresh(expense)
    return expense


def _get_job(session: Session, job_id: int) -> OcrJob:
    job = session.get(OcrJob, job_id)
    if job is None:
        raise NotFoundError("OCR job was not found.")
    return job


def _get_file(session: Session, file_id: int) -> File:
    file = session.get(File, file_id)
    if file is None:
        raise NotFoundError("File was not found.")
    return file


def _get_project(session: Session, project_id: int) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project was not found.")
    return project


def _ensure_category_exists(session: Session, category_id: int | None) -> None:
    if category_id is not None and session.get(ExpenseCategory, category_id) is None:
        raise NotFoundError("Expense category was not found.")
