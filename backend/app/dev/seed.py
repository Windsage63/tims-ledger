from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import ContractType, Customer, Project, ProjectStatus


def seed_development_data(session: Session) -> dict[str, int]:
    customer = session.scalar(select(Customer).where(Customer.name == "Air Advantage"))
    if customer is None:
        customer = Customer(
            name="Air Advantage",
            billing_email="billing@example.com",
            phone="555-0100",
            default_terms="Net 15",
            notes="Development seed customer for the first proof workflow.",
        )
        session.add(customer)
        session.flush()

    project = session.scalar(
        select(Project).where(
            Project.customer_id == customer.id,
            Project.project_no == "AA-001",
        )
    )
    if project is None:
        project = Project(
            customer_id=customer.id,
            project_no="AA-001",
            name="Tower Upgrade",
            description="Development seed project for invoice builder testing.",
            contract_type=ContractType.TIME_AND_MATERIALS.value,
            status=ProjectStatus.ACTIVE.value,
            default_hourly_rate=Decimal("125.00"),
        )
        session.add(project)
        session.flush()

    session.commit()
    return {"customers": 1, "projects": 1}


def main() -> None:
    with SessionLocal() as session:
        counts = seed_development_data(session)
    print(f"Seeded {counts['customers']} customer and {counts['projects']} project.")


if __name__ == "__main__":
    main()
