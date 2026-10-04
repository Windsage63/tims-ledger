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


# Insertion order defines sidebar order. This is also the page-route allowlist.
PAGE_REGISTRY: dict[str, Page] = {
    "index.html": Page(
        filename='index.html',
        title="Tim's Ledger",
        label='Home',
        group='',
        heading='Home',
        new_label=None,
        script_url='/frontend/js/app.js?v=20261004-phase1',
        help_text="Don't forget to back up before you close the application.",
        main_id="overview",
    ),
    "invoices.html": Page(
        filename='invoices.html',
        title="Tim's Ledger Invoices",
        label='Invoices',
        group='Sales',
        heading='Invoices',
        new_label='Invoice',
        script_url='/frontend/js/invoices.js?v=20261004-phase1',
        help_text='Invoices can be edited and re-saved. Changes will be reflected in the invoice ledger and associated projects. To edit a time or expense entry that is already on an invoice, first remove it from the invoice, then edit, then add it back.',
    ),
    "payments.html": Page(
        filename='payments.html',
        title="Tim's Ledger Payments",
        label='Receive Payments',
        group='Sales',
        heading='Receive Payments',
        new_label='Payment',
        script_url='/frontend/js/payments.js?v=20261004-phase1',
        help_text='Payments can be split among multiple invoices, but can only originate from a single customer. ',
    ),
    "customers.html": Page(
        filename='customers.html',
        title="Tim's Ledger Customers",
        label='Customers',
        group='Sales',
        heading='Customers',
        new_label='Customer',
        script_url='/frontend/js/customers.js?v=20261004-phase1',
        help_text='Maintain customer contact details and review balances. Select a row to edit, or use New Customer.',
    ),
    "projects.html": Page(
        filename='projects.html',
        title="Tim's Ledger Projects",
        label='Projects',
        group='Work',
        heading='Projects',
        new_label='Project',
        script_url='/frontend/js/projects.js?v=20261004-phase1',
        help_text='This module handles projects and rates. You can add parts pricing as custom rates and then bill by the unit on the timesheet screen.',
    ),
    "time.html": Page(
        filename='time.html',
        title="Tim's Ledger Time",
        label='Time',
        group='Work',
        heading='Time',
        new_label='Time Entry',
        script_url='/frontend/js/time.js?v=20261004-phase1',
        help_text='Insert parts units as hours and select their custom rate codes to add parts to a project.',
    ),
    "expenses.html": Page(
        filename='expenses.html',
        title="Tim's Ledger Expenses",
        label='Expenses',
        group='Work',
        heading='Expenses',
        new_label='Expense',
        script_url='/frontend/js/expenses.js?v=20261004-phase1',
        help_text='General office costs and other company expenses can be associated with an internal project and marked unbillable to track other costs. Use unbillable expenses for the costs of parts that have been sold under custom rate codes to track cost of sales for parts.',
    ),
    "company.html": Page(
        filename='company.html',
        title="Tim's Ledger Settings",
        label='Settings',
        group='Settings',
        heading='Settings',
        new_label=None,
        script_url='/frontend/js/company.js?v=20261004-phase1',
        help_text='This profile is used on newly generated invoice documents.',
        is_settings=True,
    ),
}
