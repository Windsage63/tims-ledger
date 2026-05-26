from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import ConflictError, NotFoundError
from app.db.session import get_session
from app.models import BillingStatus, Project, TimeEntry
from app.schemas.time_entries import TimeEntryCreate, TimeEntryRead, TimeEntryUpdate
from app.services import money

router = APIRouter(prefix="/time-entries", tags=["time entries"])


@router.get("", response_model=list[TimeEntryRead])
def list_time_entries(
    session: Annotated[Session, Depends(get_session)],
    customer_id: int | None = None,
    project_id: int | None = None,
    billing_status: Annotated[str | None, Query(max_length=40)] = None,
    unbilled_only: bool = False,
) -> list[TimeEntry]:
    query = select(TimeEntry).order_by(TimeEntry.date, TimeEntry.id)
    if customer_id is not None:
        query = query.where(TimeEntry.customer_id == customer_id)
    if project_id is not None:
        query = query.where(TimeEntry.project_id == project_id)
    if billing_status:
        query = query.where(TimeEntry.billing_status == billing_status)
    if unbilled_only:
        query = query.where(
            TimeEntry.billable.is_(True),
            TimeEntry.billing_status == BillingStatus.UNBILLED.value,
        )
    return list(session.scalars(query))


@router.post("", response_model=TimeEntryRead, status_code=status.HTTP_201_CREATED)
def create_time_entry(
    payload: TimeEntryCreate,
    session: Annotated[Session, Depends(get_session)],
) -> TimeEntry:
    project = _get_project(session, payload.project_id)
    rate = _resolve_rate(payload.rate, project)
    billing_status = (
        BillingStatus.UNBILLED.value if payload.billable else BillingStatus.NON_BILLABLE.value
    )
    entry = TimeEntry(
        **payload.model_dump(exclude={"rate"}),
        customer_id=project.customer_id,
        rate=rate,
        billing_status=billing_status,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


@router.get("/{time_entry_id}", response_model=TimeEntryRead)
def get_time_entry(
    time_entry_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> TimeEntry:
    return _get_time_entry(session, time_entry_id)


@router.patch("/{time_entry_id}", response_model=TimeEntryRead)
def update_time_entry(
    time_entry_id: int,
    payload: TimeEntryUpdate,
    session: Annotated[Session, Depends(get_session)],
) -> TimeEntry:
    entry = _get_time_entry(session, time_entry_id)
    _ensure_time_entry_editable(entry)
    updates = payload.model_dump(exclude_unset=True)

    project = (
        _get_project(session, updates["project_id"])
        if "project_id" in updates
        else entry.project
    )
    if "project_id" in updates:
        entry.customer_id = project.customer_id

    if "rate" in updates:
        entry.rate = _resolve_rate(updates.pop("rate"), project)
    elif "project_id" in updates and entry.rate is None:
        entry.rate = _resolve_rate(None, project)

    if "billable" in updates:
        entry.billing_status = (
            BillingStatus.UNBILLED.value
            if updates["billable"]
            else BillingStatus.NON_BILLABLE.value
        )

    for field, value in updates.items():
        setattr(entry, field, value)

    session.commit()
    session.refresh(entry)
    return entry


def _get_time_entry(session: Session, time_entry_id: int) -> TimeEntry:
    entry = session.get(TimeEntry, time_entry_id)
    if entry is None:
        raise NotFoundError("Time entry was not found.")
    return entry


def _get_project(session: Session, project_id: int) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project was not found.")
    return project


def _resolve_rate(rate: Decimal | None, project: Project) -> Decimal:
    resolved = rate if rate is not None else project.default_hourly_rate
    if resolved is None:
        raise ConflictError("Time entry requires a rate or project default hourly rate.")
    return money(resolved)


def _ensure_time_entry_editable(entry: TimeEntry) -> None:
    if entry.invoice_id is not None or entry.billing_status in {
        BillingStatus.DRAFTED.value,
        BillingStatus.INVOICED.value,
    }:
        raise ConflictError("Time entry is linked to an invoice and cannot be edited.")
