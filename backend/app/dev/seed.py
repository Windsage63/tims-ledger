from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import ContractType, Customer, ExpenseCategory, Project, ProjectStatus


def seed_development_data(session: Session) -> dict[str, int]:
    customer = session.scalar(select(Customer).where(Customer.name == "Air Advantage"))
    if customer is None:
        customer = Customer(
            name="Air Advantage",
            billing_contact_name="Accounts Payable",
            billing_email="billing@example.com",
            phone="555-0100",
            billing_address_line1="100 Aviation Way",
            billing_city="Tulsa",
            billing_state="OK",
            billing_postal_code="74101",
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

    category = session.scalar(select(ExpenseCategory).where(ExpenseCategory.name == "Materials"))
    if category is None:
        category = ExpenseCategory(
            name="Materials",
            default_billable=True,
            default_reimbursable=True,
            expense_category="Materials",
            revenue_category="Reimbursed materials",
        )
        session.add(category)
        session.flush()

    session.commit()
    return {"customers": 1, "projects": 1, "expense_categories": 1}


def main() -> None:
    with SessionLocal() as session:
        counts = seed_development_data(session)
    print(
        "Seeded "
        f"{counts['customers']} customer, "
        f"{counts['projects']} project, and "
        f"{counts['expense_categories']} expense category."
    )


if __name__ == "__main__":
    main()
