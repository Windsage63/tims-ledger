from fastapi.testclient import TestClient


def test_invoice_builder_candidates_and_invoice_issue_flow(api_client: TestClient) -> None:
    customer_id, project_id = _create_customer_project_sources(api_client)

    candidates_response = api_client.get(
        "/api/invoice-builder/candidates",
        params={"customer_id": customer_id, "project_id": project_id},
    )

    assert candidates_response.status_code == 200
    candidates = candidates_response.json()
    assert [entry["description"] for entry in candidates["time_entries"]] == ["Field labor"]
    assert [expense["description"] for expense in candidates["expenses"]] == ["Cable"]

    invoice_response = api_client.post(
        "/api/invoices",
        json={
            "invoice_no": "662",
            "customer_id": customer_id,
            "invoice_date": "2026-05-07",
            "time_entry_ids": [candidates["time_entries"][0]["id"]],
            "expense_ids": [candidates["expenses"][0]["id"]],
            "terms": "Net 15",
        },
    )

    assert invoice_response.status_code == 201
    invoice = invoice_response.json()
    assert invoice["status"] == "draft"
    assert invoice["subtotal_labor"] == "250.00"
    assert invoice["subtotal_expenses"] == "42.50"
    assert invoice["total"] == "292.50"
    assert invoice["open_balance"] == "292.50"
    assert [line["source_type"] for line in invoice["lines"]] == ["time_entry", "expense"]

    empty_candidates_response = api_client.get(
        "/api/invoice-builder/candidates",
        params={"customer_id": customer_id, "project_id": project_id},
    )
    assert empty_candidates_response.json()["time_entries"] == []
    assert empty_candidates_response.json()["expenses"] == []

    issue_response = api_client.post(
        f"/api/invoices/{invoice['id']}/issue",
        json={"sent_date": "2026-05-08"},
    )

    assert issue_response.status_code == 200
    issued_invoice = issue_response.json()
    assert issued_invoice["status"] == "issued"
    assert issued_invoice["sent_date"] == "2026-05-08"

    time_entry = api_client.get(f"/api/time-entries/{candidates['time_entries'][0]['id']}").json()
    expense = api_client.get(f"/api/expenses/{candidates['expenses'][0]['id']}").json()
    assert time_entry["billing_status"] == "assigned"
    assert expense["reimbursement_status"] == "assigned"


def test_invoice_register_filters_by_customer_and_status(api_client: TestClient) -> None:
    customer_id, _project_id = _create_customer_project_sources(api_client)
    candidates = api_client.get(
        "/api/invoice-builder/candidates",
        params={"customer_id": customer_id},
    ).json()
    invoice = api_client.post(
        "/api/invoices",
        json={
            "invoice_no": "662",
            "customer_id": customer_id,
            "invoice_date": "2026-05-07",
            "time_entry_ids": [candidates["time_entries"][0]["id"]],
            "expense_ids": [candidates["expenses"][0]["id"]],
        },
    ).json()

    list_response = api_client.get(
        "/api/invoices",
        params={"customer_id": customer_id, "status": "draft"},
    )

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [invoice["id"]]


def test_invoice_create_rejects_unavailable_source_record(api_client: TestClient) -> None:
    customer_id, _project_id = _create_customer_project_sources(api_client, billable_time=False)
    all_entries = api_client.get("/api/time-entries").json()

    response = api_client.post(
        "/api/invoices",
        json={
            "invoice_no": "662",
            "customer_id": customer_id,
            "invoice_date": "2026-05-07",
            "time_entry_ids": [all_entries[0]["id"]],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "Time entry is not available for invoicing."


def test_invoice_create_requires_source_records(api_client: TestClient) -> None:
    customer = api_client.post("/api/customers", json={"name": "Air Advantage"}).json()

    response = api_client.post(
        "/api/invoices",
        json={
            "invoice_no": "662",
            "customer_id": customer["id"],
            "invoice_date": "2026-05-07",
            "time_entry_ids": [],
            "expense_ids": [],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["message"] == (
        "Invoice cannot be created without time entries or expenses."
    )


def _create_customer_project_sources(
    api_client: TestClient,
    *,
    billable_time: bool = True,
) -> tuple[int, int]:
    customer = api_client.post("/api/customers", json={"name": "Air Advantage"}).json()
    project = api_client.post(
        "/api/projects",
        json={
            "project_no": "AA-001",
            "customer_id": customer["id"],
            "name": "Tower Upgrade",
            "default_hourly_rate": "125.00",
        },
    ).json()
    api_client.post(
        "/api/time-entries",
        json={
            "date": "2026-05-01",
            "project_id": project["id"],
            "description": "Field labor",
            "hours": "2.00",
            "billable": billable_time,
        },
    )
    api_client.post(
        "/api/expenses",
        json={
            "date": "2026-05-02",
            "project_id": project["id"],
            "description": "Cable",
            "qty": "1.00",
            "unit_cost": "42.50",
        },
    )
    return customer["id"], project["id"]
