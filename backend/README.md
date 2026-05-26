# Backend

Planned backend stack:

  - Python
  - FastAPI
  - SQLite
  - SQLAlchemy 2.x
  - Alembic migrations
  - pytest

The backend owns business rules, accounting validation, imports, exports, invoice generation, payment application, file storage, and the future OCR pipeline.

The first accounting foundation is scaffolded:

  - SQLAlchemy models for customers, projects, time entries, expenses, invoices, invoice lines, payments, payment applications, files, OCR jobs, audit events, and app settings.
  - Alembic migration `202605250001_initial_accounting_schema`.
  - Service tests for draft invoice creation, sending invoices, and applying payments safely.
