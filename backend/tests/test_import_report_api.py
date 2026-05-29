from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook


def test_workbook_preview_detects_sheets_headers_and_mapping(api_client: TestClient) -> None:
    workbook_path = _test_artifact_path("legacy.xlsx")
    workbook = Workbook()
    customers = workbook.active
    customers.title = "Customers"
    customers.append(["Name", "Billing Email", "Phone"])
    customers.append(["Air Advantage", "billing@example.com", "555-0100"])
    time_sheet = workbook.create_sheet("Time Entries")
    time_sheet.append(["Date", "Project", "Hours", "Rate"])
    workbook.save(workbook_path)

    response = api_client.post("/api/imports/workbook/preview", json={"path": str(workbook_path)})

    assert response.status_code == 200
    preview = response.json()
    assert preview["path"] == str(workbook_path)
    assert preview["sheets"][0]["name"] == "Customers"
    assert preview["sheets"][0]["headers"] == ["Name", "Billing Email", "Phone"]
    assert preview["sheets"][0]["mapping_hint"] == "customers"
    assert preview["sheets"][1]["mapping_hint"] == "time_entries"


def test_workbook_preview_missing_file_returns_not_found(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/imports/workbook/preview",
        json={"path": "C:/does/not/exist.xlsx"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_report_csv_exports(api_client: TestClient) -> None:
    customer_id, invoice_id = _sent_invoice(api_client)

    aging_response = api_client.get(
        "/api/reports/ar-aging.csv",
        params={"as_of_date": "2026-05-20"},
    )
    open_response = api_client.get("/api/reports/open-invoices.csv")

    assert aging_response.status_code == 200
    assert aging_response.headers["content-type"].startswith("text/csv")
    assert "Air Advantage" in aging_response.text
    assert "TOTAL" in aging_response.text

    assert open_response.status_code == 200
    assert f"{customer_id},Air Advantage,{invoice_id},662" in open_response.text


def _sent_invoice(api_client: TestClient) -> tuple[int, int]:
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
    time_entry = api_client.post(
        "/api/time-entries",
        json={
            "date": "2026-05-01",
            "project_id": project["id"],
            "description": "Field labor",
            "hours": "1.00",
        },
    ).json()
    invoice = api_client.post(
        "/api/invoices",
        json={
            "invoice_no": "662",
            "customer_id": customer["id"],
            "invoice_date": "2026-05-07",
            "time_entry_ids": [time_entry["id"]],
        },
    ).json()
    api_client.post(f"/api/invoices/{invoice['id']}/send", json={"sent_date": "2026-05-08"})
    return customer["id"], invoice["id"]


def _test_artifact_path(filename: str):
    path = Path("app-data/test-artifacts") / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
