from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import Settings, load_settings
from .customers import CustomerWrite, create_customer, fetch_customers, update_customer
from .db import apply_pending_migrations, connect, get_database_status
from .expenses import ExpenseWrite, create_expense, expense_bootstrap_payload, update_expense
from .invoices import InvoiceSelectionWrite, InvoiceWrite, create_invoice, ensure_invoice_pdf, invoice_bootstrap_payload, invoice_editor_payload, issue_invoice, replace_invoice_selection, update_invoice
from .overview import overview_bootstrap_payload
from .payments import PaymentApplicationsReplace, PaymentWrite, create_payment, payment_editor_payload, payments_bootstrap_payload, replace_payment_applications, update_payment
from .projects import ProjectWrite, create_project, customer_lookup, fetch_projects, update_project
from .reporting import accounts_receivable_report_payload, build_audit_export_bytes
from .time_entries import TimeEntryWrite, create_time_entry, time_bootstrap_payload, update_time_entry
import sqlite3


def response_envelope(data: dict[str, object], *, screen: str | None = None) -> dict[str, object]:
    meta: dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "v1",
    }
    if screen:
        meta["screen"] = screen

    return {
        "data": data,
        "meta": meta,
        "errors": [],
    }


def project_integrity_http_error(exc: sqlite3.IntegrityError) -> HTTPException:
    detail = str(exc).lower()
    if "project_number" in detail and "unique" in detail:
        return HTTPException(status_code=409, detail="Project number must be unique.")
    return HTTPException(status_code=422, detail="Project payload violates database constraints.")


def create_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        startup_migrations_applied: list[str] = []

        if not settings.skip_startup_migrations:
            startup_migrations_applied = apply_pending_migrations(settings)

        app.state.settings = settings
        app.state.startup_migrations_applied = startup_migrations_applied
        yield

    return lifespan


def create_app(app_settings: Settings | None = None) -> FastAPI:
    settings = app_settings or load_settings()
    static_dir = settings.repo_root / "backend" / "app" / "static"

    app = FastAPI(
        title="Winds Ledger API",
        version="0.1.0",
        lifespan=create_lifespan(settings),
    )
    app.state.settings = settings
    app.state.startup_migrations_applied = []
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    def root() -> RedirectResponse:
        return RedirectResponse(url="/static/index.html")

    @app.get("/api/health")
    def health(request: Request) -> dict[str, object]:
        try:
            status = get_database_status(request.app.state.settings)
        except Exception as exc:  # pragma: no cover - defensive bootstrap failure path
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        return {
            "status": "ok",
            "database_path": status.database_path,
            "applied_migrations": status.applied_migrations,
            "pending_migrations": status.pending_migrations,
        }

    @app.get("/api/system/status")
    def system_status(request: Request) -> dict[str, object]:
        try:
            status = get_database_status(request.app.state.settings)
        except Exception as exc:  # pragma: no cover - defensive bootstrap failure path
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        return {
            "database_path": status.database_path,
            "migrations_dir": str(request.app.state.settings.migrations_dir),
            "skip_startup_migrations": request.app.state.settings.skip_startup_migrations,
            "startup_migrations_applied": request.app.state.startup_migrations_applied,
            "applied_migrations": status.applied_migrations,
            "pending_migrations": status.pending_migrations,
            "table_count": status.table_count,
            "view_count": status.view_count,
        }

    @app.get("/api/overview/bootstrap")
    def overview_bootstrap(request: Request) -> dict[str, object]:
        try:
            status = get_database_status(request.app.state.settings)
        except Exception as exc:  # pragma: no cover - defensive bootstrap failure path
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        with connect(request.app.state.settings.database_path) as connection:
            payload = overview_bootstrap_payload(connection)

        payload["system"] = {
            "database_path": status.database_path,
            "applied_migrations_count": len(status.applied_migrations),
            "pending_migrations_count": len(status.pending_migrations),
        }
        return response_envelope(payload, screen="overview")

    @app.get("/api/reports/accounts-receivable")
    def accounts_receivable_report(request: Request, customer_id: int | None = None) -> dict[str, object]:
        with connect(request.app.state.settings.database_path) as connection:
            payload = accounts_receivable_report_payload(connection, customer_id=customer_id)

        if customer_id is not None and payload["statement"] is None:
            raise HTTPException(status_code=404, detail="Customer not found.")

        return response_envelope(payload, screen="accounts_receivable")

    @app.get("/api/exports/audit.xlsx")
    def audit_export(request: Request) -> Response:
        with connect(request.app.state.settings.database_path) as connection:
            workbook = build_audit_export_bytes(connection)

        return Response(
            content=workbook,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="winds-ledger-audit-export.xlsx"',
            },
        )

    @app.get("/api/customers/bootstrap")
    def customers_bootstrap(request: Request) -> dict[str, object]:
        with connect(request.app.state.settings.database_path) as connection:
            customers = fetch_customers(connection)

        return response_envelope({"customers": customers}, screen="customers")

    @app.post("/api/customers")
    def customers_create(payload: CustomerWrite, request: Request) -> dict[str, object]:
        with connect(request.app.state.settings.database_path) as connection:
            customer = create_customer(connection, payload)

        return response_envelope({"customer": customer}, screen="customers")

    @app.put("/api/customers/{customer_id}")
    def customers_update(
        customer_id: int,
        payload: CustomerWrite,
        request: Request,
    ) -> dict[str, object]:
        with connect(request.app.state.settings.database_path) as connection:
            customer = update_customer(connection, customer_id, payload)

        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found.")

        return response_envelope({"customer": customer}, screen="customers")

    @app.get("/api/projects/bootstrap")
    def projects_bootstrap(request: Request) -> dict[str, object]:
        with connect(request.app.state.settings.database_path) as connection:
            projects = fetch_projects(connection)
            customers = customer_lookup(connection)

        return response_envelope(
            {
                "projects": projects,
                "customers": customers,
            },
            screen="projects",
        )

    @app.post("/api/projects")
    def projects_create(payload: ProjectWrite, request: Request) -> dict[str, object]:
        try:
            with connect(request.app.state.settings.database_path) as connection:
                project = create_project(connection, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except sqlite3.IntegrityError as exc:
            raise project_integrity_http_error(exc) from exc

        return response_envelope({"project": project}, screen="projects")

    @app.put("/api/projects/{project_id}")
    def projects_update(
        project_id: int,
        payload: ProjectWrite,
        request: Request,
    ) -> dict[str, object]:
        try:
            with connect(request.app.state.settings.database_path) as connection:
                project = update_project(connection, project_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except sqlite3.IntegrityError as exc:
            raise project_integrity_http_error(exc) from exc

        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")

        return response_envelope({"project": project}, screen="projects")

    @app.get("/api/time/bootstrap")
    def time_bootstrap(request: Request, year: str | None = None) -> dict[str, object]:
        with connect(request.app.state.settings.database_path) as connection:
            payload = time_bootstrap_payload(connection, year=year)

        return response_envelope(payload, screen="time")

    @app.post("/api/time-entries")
    def time_entries_create(payload: TimeEntryWrite, request: Request) -> dict[str, object]:
        try:
            with connect(request.app.state.settings.database_path) as connection:
                entry = create_time_entry(connection, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return response_envelope({"entry": entry}, screen="time")

    @app.put("/api/time-entries/{entry_id}")
    def time_entries_update(
        entry_id: int,
        payload: TimeEntryWrite,
        request: Request,
    ) -> dict[str, object]:
        try:
            with connect(request.app.state.settings.database_path) as connection:
                entry = update_time_entry(connection, entry_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if entry is None:
            raise HTTPException(status_code=404, detail="Time entry not found.")

        return response_envelope({"entry": entry}, screen="time")

    @app.get("/api/expenses/bootstrap")
    def expenses_bootstrap(request: Request, year: str | None = None) -> dict[str, object]:
        with connect(request.app.state.settings.database_path) as connection:
            payload = expense_bootstrap_payload(connection, year=year)

        return response_envelope(payload, screen="expenses")

    @app.post("/api/expenses")
    def expenses_create(payload: ExpenseWrite, request: Request) -> dict[str, object]:
        try:
            with connect(request.app.state.settings.database_path) as connection:
                expense = create_expense(connection, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return response_envelope({"expense": expense}, screen="expenses")

    @app.put("/api/expenses/{expense_id}")
    def expenses_update(
        expense_id: int,
        payload: ExpenseWrite,
        request: Request,
    ) -> dict[str, object]:
        try:
            with connect(request.app.state.settings.database_path) as connection:
                expense = update_expense(connection, expense_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if expense is None:
            raise HTTPException(status_code=404, detail="Expense not found.")

        return response_envelope({"expense": expense}, screen="expenses")

    @app.get("/api/invoices/bootstrap")
    def invoices_bootstrap(request: Request, year: str | None = None) -> dict[str, object]:
        with connect(request.app.state.settings.database_path) as connection:
            payload = invoice_bootstrap_payload(connection, year=year)

        return response_envelope(payload, screen="invoices")

    @app.get("/api/invoices/{invoice_id}/editor")
    def invoices_editor(invoice_id: int, request: Request) -> dict[str, object]:
        with connect(request.app.state.settings.database_path) as connection:
            payload = invoice_editor_payload(connection, invoice_id)

        if payload is None:
            raise HTTPException(status_code=404, detail="Invoice not found.")

        return response_envelope(payload, screen="invoice_editor")

    @app.get("/api/invoices/{invoice_id}/pdf")
    def invoices_pdf(invoice_id: int, request: Request) -> FileResponse:
        try:
            with connect(request.app.state.settings.database_path) as connection:
                pdf_path = ensure_invoice_pdf(connection, invoice_id, request.app.state.settings.data_dir)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if pdf_path is None:
            raise HTTPException(status_code=404, detail="Invoice not found.")

        return FileResponse(path=pdf_path, media_type="application/pdf", filename=pdf_path.name)

    @app.post("/api/invoices")
    def invoices_create(payload: InvoiceWrite, request: Request) -> dict[str, object]:
        try:
            with connect(request.app.state.settings.database_path) as connection:
                invoice = create_invoice(connection, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Invoice number must be unique.") from exc

        return response_envelope({"invoice": invoice}, screen="invoices")

    @app.put("/api/invoices/{invoice_id}")
    def invoices_update(invoice_id: int, payload: InvoiceWrite, request: Request) -> dict[str, object]:
        try:
            with connect(request.app.state.settings.database_path) as connection:
                invoice = update_invoice(connection, invoice_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Invoice number must be unique.") from exc

        if invoice is None:
            raise HTTPException(status_code=404, detail="Invoice not found.")

        return response_envelope({"invoice": invoice}, screen="invoices")

    @app.post("/api/invoices/{invoice_id}/selection")
    def invoices_selection(invoice_id: int, payload: InvoiceSelectionWrite, request: Request) -> dict[str, object]:
        try:
            with connect(request.app.state.settings.database_path) as connection:
                editor_payload = replace_invoice_selection(connection, invoice_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if editor_payload is None:
            raise HTTPException(status_code=404, detail="Invoice not found.")

        return response_envelope(editor_payload, screen="invoice_editor")

    @app.post("/api/invoices/{invoice_id}/issue")
    def invoices_issue(invoice_id: int, request: Request) -> dict[str, object]:
        try:
            with connect(request.app.state.settings.database_path) as connection:
                issue_payload = issue_invoice(connection, invoice_id, request.app.state.settings.data_dir)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if issue_payload is None:
            raise HTTPException(status_code=404, detail="Invoice not found.")

        return response_envelope(issue_payload, screen="invoice_editor")

    @app.get("/api/payments/bootstrap")
    def payments_bootstrap(request: Request, year: str | None = None) -> dict[str, object]:
        with connect(request.app.state.settings.database_path) as connection:
            payload = payments_bootstrap_payload(connection, year=year)

        return response_envelope(payload, screen="payments")

    @app.get("/api/payments/{payment_id}/editor")
    def payments_editor(payment_id: int, request: Request) -> dict[str, object]:
        with connect(request.app.state.settings.database_path) as connection:
            payload = payment_editor_payload(connection, payment_id)

        if payload is None:
            raise HTTPException(status_code=404, detail="Payment not found.")

        return response_envelope(payload, screen="payment_editor")

    @app.post("/api/payments")
    def payments_create(payload: PaymentWrite, request: Request) -> dict[str, object]:
        try:
            with connect(request.app.state.settings.database_path) as connection:
                payment = create_payment(connection, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return response_envelope({"payment": payment}, screen="payments")

    @app.put("/api/payments/{payment_id}")
    def payments_update(payment_id: int, payload: PaymentWrite, request: Request) -> dict[str, object]:
        try:
            with connect(request.app.state.settings.database_path) as connection:
                payment = update_payment(connection, payment_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if payment is None:
            raise HTTPException(status_code=404, detail="Payment not found.")

        return response_envelope({"payment": payment}, screen="payments")

    @app.post("/api/payments/{payment_id}/applications")
    def payments_replace_applications(payment_id: int, payload: PaymentApplicationsReplace, request: Request) -> dict[str, object]:
        try:
            with connect(request.app.state.settings.database_path) as connection:
                editor_payload = replace_payment_applications(connection, payment_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if editor_payload is None:
            raise HTTPException(status_code=404, detail="Payment not found.")

        return response_envelope(editor_payload, screen="payment_editor")

    return app


app = create_app()