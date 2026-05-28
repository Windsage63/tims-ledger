# ADR 0001: Local-First FastAPI, React, and SQLite

## Status

Accepted as initial direction.

## Context

Windsage Ledger is a small-business accounting operations app intended to replace fragile spreadsheet workflows. The app needs strong support for data import, accounting rules, PDF/Excel output, and future receipt OCR, while still providing a modern interactive interface.

## Decision

Use:

  - Python and FastAPI for the backend
  - React and TypeScript for the frontend
  - SQLite for the initial local-first database

## Alternatives Considered

  - Node backend with React frontend
  - Plain HTML and JavaScript
  - Desktop-native app from the beginning
  - PostgreSQL from the beginning

## Consequences

This keeps business logic and automation in Python, where spreadsheet import, document generation, OCR work, and invoice or payment workflows are strongest. React adds frontend build complexity, but it is the better fit for invoice building, editable tables, draft review workflows, filters, and approval screens. SQLite keeps setup and backup simple for the first version, and the local-first model extends to app-managed receipts and generated PDFs, but the data layer should avoid assumptions that would make a later PostgreSQL migration painful.
