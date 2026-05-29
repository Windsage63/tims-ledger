from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import ConflictError
from app.api.errors import NotFoundError
from app.db.session import get_session
from app.models import Customer, Project
from app.schemas.projects import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(
    session: Annotated[Session, Depends(get_session)],
    customer_id: int | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    status: Annotated[str | None, Query(max_length=40)] = None,
) -> list[Project]:
    query = select(Project).order_by(Project.name)
    if customer_id is not None:
        query = query.where(Project.customer_id == customer_id)
    if search:
        query = query.where(Project.name.ilike(f"%{search}%"))
    if status:
        query = query.where(Project.status == status)
    return list(session.scalars(query))


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Project:
    _ensure_customer_exists(session, payload.customer_id)
    _ensure_project_no_available(session, payload.project_no)
    project = Project(**payload.model_dump())
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> Project:
    return _get_project(session, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    session: Annotated[Session, Depends(get_session)],
) -> Project:
    project = _get_project(session, project_id)
    updates = payload.model_dump(exclude_unset=True)
    if "customer_id" in updates:
        _ensure_customer_exists(session, updates["customer_id"])
    if "project_no" in updates:
        _ensure_project_no_available(session, updates["project_no"], project_id=project_id)

    for field, value in updates.items():
        setattr(project, field, value)

    session.commit()
    session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_project(
    project_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    project = _get_project(session, project_id)
    project.status = "inactive"
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _get_project(session: Session, project_id: int) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project was not found.")
    return project


def _ensure_customer_exists(session: Session, customer_id: int) -> None:
    if session.get(Customer, customer_id) is None:
        raise NotFoundError("Customer was not found.")


def _ensure_project_no_available(
    session: Session,
    project_no: str,
    *,
    project_id: int | None = None,
) -> None:
    existing = session.scalar(select(Project).where(Project.project_no == project_no))
    if existing is not None and existing.id != project_id:
        raise ConflictError("Project number already exists.")
