from fastapi.testclient import TestClient


def test_customer_crud_flow(api_client: TestClient) -> None:
    create_response = api_client.post(
        "/api/customers",
        json={
            "name": "Air Advantage",
            "billing_email": "billing@example.com",
            "phone": "555-0100",
            "default_terms": "Net 15",
            "notes": "Primary proof customer",
        },
    )

    assert create_response.status_code == 201
    customer = create_response.json()
    assert customer["id"] > 0
    assert customer["name"] == "Air Advantage"
    assert customer["active"] is True

    list_response = api_client.get("/api/customers", params={"search": "Air"})

    assert list_response.status_code == 200
    assert [item["name"] for item in list_response.json()] == ["Air Advantage"]

    update_response = api_client.patch(
        f"/api/customers/{customer['id']}",
        json={"phone": "555-0199", "notes": "Updated"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["phone"] == "555-0199"

    delete_response = api_client.delete(f"/api/customers/{customer['id']}")

    assert delete_response.status_code == 204
    detail_response = api_client.get(f"/api/customers/{customer['id']}")
    assert detail_response.json()["active"] is False


def test_duplicate_customer_name_returns_consistent_error(api_client: TestClient) -> None:
    payload = {"name": "Air Advantage"}

    assert api_client.post("/api/customers", json=payload).status_code == 201
    response = api_client.post("/api/customers", json=payload)

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "CONFLICT",
            "message": "Customer name already exists.",
            "details": [],
        }
    }


def test_project_crud_flow(api_client: TestClient) -> None:
    customer_response = api_client.post("/api/customers", json={"name": "Air Advantage"})
    customer_id = customer_response.json()["id"]

    create_response = api_client.post(
        "/api/projects",
        json={
            "project_no": "AA-001",
            "customer_id": customer_id,
            "name": "Tower Upgrade",
            "description": "Initial proof project",
            "contract_type": "time_and_materials",
            "status": "active",
            "default_hourly_rate": "125.00",
        },
    )

    assert create_response.status_code == 201
    project = create_response.json()
    assert project["id"] > 0
    assert project["customer_id"] == customer_id
    assert project["default_hourly_rate"] == "125.00"

    list_response = api_client.get("/api/projects", params={"customer_id": customer_id})

    assert list_response.status_code == 200
    assert [item["name"] for item in list_response.json()] == ["Tower Upgrade"]

    update_response = api_client.patch(
        f"/api/projects/{project['id']}",
        json={"status": "completed", "fixed_fee_amount": "500.00"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "completed"
    assert update_response.json()["fixed_fee_amount"] == "500.00"

    delete_response = api_client.delete(f"/api/projects/{project['id']}")

    assert delete_response.status_code == 204
    detail_response = api_client.get(f"/api/projects/{project['id']}")
    assert detail_response.json()["status"] == "inactive"


def test_project_create_requires_existing_customer(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/projects",
        json={
            "customer_id": 999,
            "name": "Missing customer project",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_validation_errors_use_api_error_shape(api_client: TestClient) -> None:
    response = api_client.post("/api/customers", json={"name": ""})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"][0]["loc"] == ["body", "name"]
