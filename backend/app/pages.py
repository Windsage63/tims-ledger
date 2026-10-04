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
    group: str
    heading: str
    help_text: str
    new_label: str | None = None
    is_settings: bool = False
    main_id: str | None = None
    supports_edit_mode: bool = False


# Insertion order defines sidebar order. This is also the page-route allowlist.
PAGE_REGISTRY: dict[str, Page] = {
    "index.html": Page(
        filename='index.html',
        title="Tim's Ledger",
        label='Home',
        group='',
        heading='Home',
        new_label=None,
        script_url='/frontend/js/app.js?v=20261004-business-totals',
        help_text="Use the sidebar to manage your work and billing. Business totals are on Receive Payments; customer statements are on Customers. Back up before closing the application.",
        main_id="overview",
    ),
    "invoices.html": Page(
        filename='invoices.html',
        supports_edit_mode=True,
        title="Tim's Ledger Invoices",
        label='Invoices',
        group='Sales',
        heading='Invoices',
        new_label='Invoice',
        script_url='/frontend/js/invoices.js?v=20261004-phase2',
        help_text='Invoices can be edited and re-saved. Changes will be reflected in the invoice ledger and associated projects. To edit a time or expense entry that is already on an invoice, first remove it from the invoice, then edit, then add it back.',
    ),
    "payments.html": Page(
        filename='payments.html',
        supports_edit_mode=True,
        title="Tim's Ledger Payments",
        label='Receive Payments',
        group='Sales',
        heading='Receive Payments',
        new_label='Payment',
        script_url='/frontend/js/payments.js?v=20261004-business-totals',
        help_text='Business totals cover all saved records and are unaffected by ledger filters. Total Income includes unapplied payments and negative corrections. Payments can be split among multiple invoices, but can only originate from a single customer.',
    ),
    "customers.html": Page(
        filename='customers.html',
        supports_edit_mode=True,
        title="Tim's Ledger Customers",
        label='Customers',
        group='Sales',
        heading='Customers',
        new_label='Customer',
        script_url='/frontend/js/customers.js?v=20261004-phase2',
        help_text='Maintain customer contact details and review balances. Select a row to view contact details and its statement. Enable Edit Mode to change an existing customer, or use New Customer.',
    ),
    "projects.html": Page(
        filename='projects.html',
        supports_edit_mode=True,
        title="Tim's Ledger Projects",
        label='Projects',
        group='Work',
        heading='Projects',
        new_label='Project',
        script_url='/frontend/js/projects.js?v=20261004-phase2',
        help_text='This module handles projects and rates. You can add parts pricing as custom rates and then bill by the unit on the timesheet screen.',
    ),
    "time.html": Page(
        filename='time.html',
        supports_edit_mode=True,
        title="Tim's Ledger Time",
        label='Time',
        group='Work',
        heading='Time',
        new_label='Time Entry',
        script_url='/frontend/js/time.js?v=20261004-phase2',
        help_text='Insert parts units as hours and select their custom rate codes to add parts to a project.',
    ),
    "expenses.html": Page(
        filename='expenses.html',
        supports_edit_mode=True,
        title="Tim's Ledger Expenses",
        label='Expenses',
        group='Work',
        heading='Expenses',
        new_label='Expense',
        script_url='/frontend/js/expenses.js?v=20261004-phase2',
        help_text='General office costs and other company expenses can be associated with an internal project and marked unbillable to track other costs. Use unbillable expenses for the costs of parts that have been sold under custom rate codes to track cost of sales for parts.',
    ),
    "company.html": Page(
        filename='company.html',
        title="Tim's Ledger Settings",
        label='Settings',
        group='Settings',
        heading='Settings',
        new_label=None,
        script_url='/frontend/js/company.js?v=20261004-phase2',
        help_text='This profile is used on newly generated invoice documents.',
        is_settings=True,
    ),
}
