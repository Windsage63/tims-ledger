from fastapi.testclient import TestClient


def test_payment_application_and_customer_balance_flow(api_client: TestClient) -> None:
    customer_id, invoice_id = _sent_invoice(api_client, invoice_no="662")
    payment_response = api_client.post(
        "/api/payments",
        json={
            "customer_id": customer_id,
            "payment_date": "2026-05-10",
            "payment_type": "customer_payment",
            "reference_no": "CHK-100",
            "amount_received": "300.00",
        },
    )

    assert payment_response.status_code == 201
    payment = payment_response.json()
    assert payment["unapplied_amount"] == "300.00"

    apply_response = api_client.post(
        f"/api/payments/{payment['id']}/applications",
        json={
            "application_date": "2026-05-10",
            "applications": [{"invoice_id": invoice_id, "amount": "100.00"}],
        },
    )

    assert apply_response.status_code == 200
    assert apply_response.json()[0]["amount_applied"] == "100.00"

    invoice = api_client.get(f"/api/invoices/{invoice_id}").json()
    payment = api_client.get(f"/api/payments/{payment['id']}").json()
    balance = api_client.get(f"/api/customers/{customer_id}/balance").json()
    assert invoice["status"] == "partially_paid"
    assert invoice["open_balance"] == "25.00"
    assert payment["unapplied_amount"] == "200.00"
    assert balance == {
        "customer_id": customer_id,
        "open_ar": "25.00",
        "unapplied_credits": "200.00",
        "net_balance": "-175.00",
        "open_invoice_count": 1,
        "unapplied_payment_count": 1,
    }


def test_payment_application_rejects_cross_customer_invoice(api_client: TestClient) -> None:
    customer_id, _invoice_id = _sent_invoice(api_client, invoice_no="662")
    _other_customer_id, other_invoice_id = _sent_invoice(
        api_client,
        invoice_no="663",
        customer_name="Other Customer",
    )
    payment = api_client.post(
        "/api/payments",
        json={
            "customer_id": customer_id,
            "payment_date": "2026-05-10",
            "amount_received": "125.00",
        },
    ).json()

    response = api_client.post(
        f"/api/payments/{payment['id']}/applications",
        json={
            "application_date": "2026-05-10",
            "applications": [{"invoice_id": other_invoice_id, "amount": "25.00"}],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["message"] == (
        "Payment cannot be applied to another customer's invoice."
    )


def test_ar_aging_report_buckets_open_invoices(api_client: TestClient) -> None:
    customer_id, invoice_id = _sent_invoice(api_client, invoice_no="662", due_date="2026-05-15")

    response = api_client.get("/api/reports/ar-aging", params={"as_of_date": "2026-06-20"})

    assert response.status_code == 200
    report = response.json()
    assert report["as_of_date"] == "2026-06-20"
    assert report["total"] == "125.00"
    assert report["customers"] == [
        {
            "customer_id": customer_id,
            "customer_name": "Air Advantage",
            "current": "0.00",
            "days_1_30": "0.00",
            "days_31_60": "125.00",
            "days_61_90": "0.00",
            "days_over_90": "0.00",
            "total": "125.00",
        }
    ]
    assert api_client.get(f"/api/invoices/{invoice_id}").status_code == 200


def _sent_invoice(
    api_client: TestClient,
    *,
    invoice_no: str,
    customer_name: str = "Air Advantage",
    due_date: str | None = None,
) -> tuple[int, int]:
    customer = api_client.post("/api/customers", json={"name": customer_name}).json()
    project = api_client.post(
        "/api/projects",
        json={
            "project_no": f"{invoice_no}-PRJ",
            "customer_id": customer["id"],
            "name": f"{customer_name} Tower Upgrade",
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
    payload = {
        "invoice_no": invoice_no,
        "customer_id": customer["id"],
        "invoice_date": "2026-05-07",
        "time_entry_ids": [time_entry["id"]],
    }
    if due_date is not None:
        payload["due_date"] = due_date
    invoice = api_client.post("/api/invoices", json=payload).json()
    api_client.post(f"/api/invoices/{invoice['id']}/send", json={"sent_date": "2026-05-08"})
    return customer["id"], invoice["id"]
