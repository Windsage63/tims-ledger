from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dev.seed import seed_development_data
from app.models import Customer, Project


def test_development_seed_is_idempotent(session: Session) -> None:
    seed_development_data(session)
    seed_development_data(session)

    customers = list(session.scalars(select(Customer)))
    projects = list(session.scalars(select(Project)))

    assert [customer.name for customer in customers] == ["Air Advantage"]
    assert [project.project_no for project in projects] == ["AA-001"]
