"""
@fileoverview Define allowed pages, navigation order, and shared layout metadata.
@license Apache-2.0
@copyright 2026 Timothy Mallory
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    filename: str
    title: str
    label: str
    script_url: str
    sidebar_label: str
    sidebar_status_id: str
    sidebar_help: str
    is_settings: bool = False
    main_id: str | None = None


# Insertion order defines sidebar order. This is also the page-route allowlist.
PAGE_REGISTRY: dict[str, Page] = {
    "index.html": Page(
        filename='index.html',
        title="Tim's Ledger",
        label='Overview',
        script_url='/frontend/js/app.js',
        sidebar_label='Accounts Receivable',
        sidebar_status_id='app-mode',
        sidebar_help="Don't forget to back up before you close the application.",
        main_id="overview",
    ),
    "customers.html": Page(
        filename='customers.html',
        title="Tim's Ledger Customers",
        label='Customers',
        script_url='/frontend/js/customers.js',
        sidebar_label='Customers Module',
        sidebar_status_id='customer-mode',
        sidebar_help='This module loads customer records from the backend exercising the database path.',
    ),
    "projects.html": Page(
        filename='projects.html',
        title="Tim's Ledger Projects",
        label='Projects',
        script_url='/frontend/js/projects.js?v=20260614-custom-rate-focus',
        sidebar_label='Projects Module',
        sidebar_status_id='projects-mode',
        sidebar_help='This module handles projects and rates. You can add parts pricing as custom rates and then bill by the unit on the timesheet screen.',
    ),
    "time.html": Page(
        filename='time.html',
        title="Tim's Ledger Time",
        label='Time',
        script_url='/frontend/js/time.js?v=20260614-project-description',
        sidebar_label='Time Module',
        sidebar_status_id='time-mode',
        sidebar_help='Insert parts units as hours and select their custom rate codes to add parts to a project.',
    ),
    "expenses.html": Page(
        filename='expenses.html',
        title="Tim's Ledger Expenses",
        label='Expenses',
        script_url='/frontend/js/expenses.js?v=20260614-project-description',
        sidebar_label='Expenses Module',
        sidebar_status_id='expenses-mode',
        sidebar_help='General office costs and other company expenses can be associated with an internal project and marked unbillable to track other costs. Use unbillable expenses for the costs of parts that have been sold under custom rate codes to track cost of sales for parts.',
    ),
    "invoices.html": Page(
        filename='invoices.html',
        title="Tim's Ledger Invoices",
        label='Invoices',
        script_url='/frontend/js/invoices.js?v=20260614-1',
        sidebar_label='Invoices Module',
        sidebar_status_id='invoices-mode',
        sidebar_help='Invoices can be edited and re-saved. Changes will be reflected in the invoice ledger and associated projects. To edit a time or expense entry that is already on an invoice, first remove it from the invoice, then edit, then add it back.',
    ),
    "payments.html": Page(
        filename='payments.html',
        title="Tim's Ledger Payments",
        label='Payments',
        script_url='/frontend/js/payments.js',
        sidebar_label='Payments Module',
        sidebar_status_id='payments-mode',
        sidebar_help='Payments can be split among multiple invoices, but can only originate from a single customer. ',
    ),
    "company.html": Page(
        filename='company.html',
        title="Tim's Ledger Company",
        label='Company',
        script_url='/frontend/js/company.js',
        sidebar_label='Company Profile',
        sidebar_status_id='company-mode',
        sidebar_help='This profile is used on newly generated invoice documents.',
        is_settings=True,
    ),
}
