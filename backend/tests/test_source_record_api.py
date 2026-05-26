from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Customer, Expense, Project, TimeEntry
from app.services import create_draft_invoice_from_sources, send_invoice


def test_time_entry_create_uses_project_customer_and_default_rate(api_client: TestClient) -> None:
    customer_id, project_id = _create_customer_and_project(api_client)

    response = api_client.post(
        "/api/time-entries",
        json={
            "date": "2026-05-01",
            "project_id": project_id,
            "description": "Field labor",
            "hours": "2.50",
            "billable": True,
        },
    )

    assert response.status_code == 201
    entry = response.json()
    assert entry["customer_id"] == customer_id
    assert entry["project_id"] == project_id
    assert entry["rate"] == "125.00"
    assert entry["billing_status"] == "unbilled"


def test_time_entry_unbilled_filter_excludes_nonbillable(api_client: TestClient) -> None:
    _customer_id, project_id = _create_customer_and_project(api_client)
    api_client.post(
        "/api/time-entries",
        json={
            "date": "2026-05-01",
            "project_id": project_id,
            "description": "Billable field labor",
            "hours": "1.00",
            "billable": True,
        },
    )
    api_client.post(
        "/api/time-entries",
        json={
            "date": "2026-05-02",
            "project_id": project_id,
            "description": "Internal admin",
            "hours": "1.00",
            "billable": False,
        },
    )

    response = api_client.get("/api/time-entries", params={"unbilled_only": True})

    assert response.status_code == 200
    assert [entry["description"] for entry in response.json()] == ["Billable field labor"]


def test_expense_category_and_expense_flow(api_client: TestClient) -> None:
    customer_id, project_id = _create_customer_and_project(api_client)
    category_response = api_client.post(
        "/api/expense-categories",
        json={
            "name": "Materials",
            "default_billable": True,
            "default_reimbursable": True,
        },
    )
    category_id = category_response.json()["id"]

    response = api_client.post(
        "/api/expenses",
        json={
            "date": "2026-05-02",
            "project_id": project_id,
            "category_id": category_id,
            "vendor": "Supply House",
            "description": "Cable",
            "qty": "3.00",
            "unit_cost": "12.50",
            "billable": True,
            "reimbursable": True,
        },
    )

    assert response.status_code == 201
    expense = response.json()
    assert expense["customer_id"] == customer_id
    assert expense["total"] == "37.50"
    assert expense["reimbursement_status"] == "unbilled"

    list_response = api_client.get("/api/expenses", params={"unbilled_only": True})

    assert [item["description"] for item in list_response.json()] == ["Cable"]


def test_expense_unbilled_filter_excludes_nonreimbursable(api_client: TestClient) -> None:
    _customer_id, project_id = _create_customer_and_project(api_client)
    for description, reimbursable in [
        ("Billable material", True),
        ("Internal tool", False),
    ]:
        api_client.post(
            "/api/expenses",
            json={
                "date": "2026-05-02",
                "project_id": project_id,
                "description": description,
                "qty": "1.00",
                "unit_cost": "10.00",
                "billable": True,
                "reimbursable": reimbursable,
            },
        )

    response = api_client.get("/api/expenses", params={"unbilled_only": True})

    assert response.status_code == 200
    assert [expense["description"] for expense in response.json()] == ["Billable material"]


def test_invoice_linked_source_records_cannot_be_updated(
    api_client: TestClient,
    session: Session,
) -> None:
    customer = Customer(name="Air Advantage")
    project = Project(
        customer=customer,
        name="Tower Upgrade",
        default_hourly_rate=Decimal("125.00"),
    )
    time_entry = TimeEntry(
        customer=customer,
        project=project,
        date=date(2026, 5, 1),
        description="Field labor",
        hours=Decimal("1.00"),
        rate=Decimal("125.00"),
    )
    expense = Expense(
        customer=customer,
        project=project,
        date=date(2026, 5, 2),
        description="Cable",
        qty=Decimal("1.00"),
        unit_cost=Decimal("42.00"),
        total=Decimal("42.00"),
    )
    session.add_all([customer, project, time_entry, expense])
    session.flush()
    invoice = create_draft_invoice_from_sources(
        session,
        invoice_no="662",
        customer_id=customer.id,
        invoice_date=date(2026, 5, 7),
        time_entry_ids=[time_entry.id],
        expense_ids=[expense.id],
    )
    send_invoice(session, invoice.id, sent_date=date(2026, 5, 8))
    session.commit()

    time_response = api_client.patch(
        f"/api/time-entries/{time_entry.id}",
        json={"description": "Changed"},
    )
    expense_response = api_client.patch(
        f"/api/expenses/{expense.id}",
        json={"description": "Changed"},
    )

    assert time_response.status_code == 409
    assert time_response.json()["error"]["message"] == (
        "Time entry is linked to an invoice and cannot be edited."
    )
    assert expense_response.status_code == 409
    assert expense_response.json()["error"]["message"] == (
        "Expense is linked to an invoice and cannot be edited."
    )


def test_time_entry_requires_rate_when_project_has_no_default(api_client: TestClient) -> None:
    customer_response = api_client.post("/api/customers", json={"name": "Air Advantage"})
    project_response = api_client.post(
        "/api/projects",
        json={"customer_id": customer_response.json()["id"], "name": "No Rate Project"},
    )

    response = api_client.post(
        "/api/time-entries",
        json={
            "date": "2026-05-01",
            "project_id": project_response.json()["id"],
            "description": "Field labor",
            "hours": "2.50",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["message"] == (
        "Time entry requires a rate or project default hourly rate."
    )


def _create_customer_and_project(api_client: TestClient) -> tuple[int, int]:
    customer_response = api_client.post("/api/customers", json={"name": "Air Advantage"})
    customer_id = customer_response.json()["id"]
    project_response = api_client.post(
        "/api/projects",
        json={
            "customer_id": customer_id,
            "name": "Tower Upgrade",
            "default_hourly_rate": "125.00",
        },
    )
    return customer_id, project_response.json()["id"]
