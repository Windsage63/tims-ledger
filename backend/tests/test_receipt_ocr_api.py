from pathlib import Path

from fastapi.testclient import TestClient


def test_receipt_ocr_review_creates_expense(api_client: TestClient) -> None:
    receipt_path = _test_artifact_path("receipt.txt")
    receipt_path.write_text("Supply House receipt 42.50", encoding="utf-8")
    customer = api_client.post("/api/customers", json={"name": "Air Advantage"}).json()
    project = api_client.post(
        "/api/projects",
        json={"project_no": "AA-001", "customer_id": customer["id"], "name": "Tower Upgrade"},
    ).json()

    receipt_response = api_client.post(
        "/api/receipts",
        json={"path": str(receipt_path), "mime_type": "text/plain"},
    )

    assert receipt_response.status_code == 201
    receipt = receipt_response.json()
    assert receipt["file"]["original_name"] == "receipt.txt"
    assert receipt["ocr_job"]["status"] == "pending"

    suggestions_response = api_client.patch(
        f"/api/ocr-jobs/{receipt['ocr_job']['id']}/suggestions",
        json={
            "provider": "manual-test",
            "extracted_json": {"vendor": "Supply House", "total": "42.50"},
            "confidence": "0.9200",
        },
    )

    assert suggestions_response.status_code == 200
    assert suggestions_response.json()["status"] == "needs_review"

    review_response = api_client.post(
        f"/api/ocr-jobs/{receipt['ocr_job']['id']}/review",
        json={
            "reviewed_by": "tester",
            "project_id": project["id"],
            "date": "2026-05-02",
            "vendor": "Supply House",
            "description": "Cable",
            "qty": "1.00",
            "unit_cost": "42.50",
            "billable": True,
            "reimbursable": True,
        },
    )

    assert review_response.status_code == 200
    expense = review_response.json()
    assert expense["customer_id"] == customer["id"]
    assert expense["receipt_file_id"] == receipt["file"]["id"]
    assert expense["total"] == "42.50"
    assert expense["reimbursement_status"] == "unbilled"

    job = api_client.get(f"/api/ocr-jobs/{receipt['ocr_job']['id']}").json()
    assert job["status"] == "approved"
    assert job["reviewed_by"] == "tester"


def test_missing_receipt_path_returns_validation_error(api_client: TestClient) -> None:
    response = api_client.post("/api/receipts", json={"path": "C:/missing/receipt.txt"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def _test_artifact_path(filename: str) -> Path:
    path = Path("app-data/test-artifacts") / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
