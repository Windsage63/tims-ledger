/**
 * @fileoverview Control Home metrics, accounts receivable, and customer statements.
 * @license Apache-2.0
 * @copyright 2026 Timothy Mallory
 */

const reportState = { summary: {}, customers: [], selectedCustomerId: null, statement: null };

function renderOverview(data) {
    setText("metric-assets", currency(data.summary?.unbilled_work_cents || 0));
}

function renderOverviewError(message) {
    setText("metric-assets", "—");
    showToast(message);
}

function customerAddress(customer) {
    if (!customer) {
        return "";
    }
    return [customer.street_address, `${customer.city}, ${customer.state} ${customer.zip}`].filter(Boolean).join(" · ");
}

function statementTimestamp(value) {
    if (!value) {
        return "Statement unavailable";
    }
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? value : `Generated ${parsed.toLocaleString()}`;
}

function renderAccountsReceivable() {
    const summary = reportState.summary || {};
    const customers = Array.isArray(reportState.customers) ? reportState.customers : [];
    const statement = reportState.statement || null;

    setText("ar-total-open", currency(summary.total_open_ar_cents || 0));
    setText("ar-total-credit", currency(summary.total_unapplied_credit_cents || 0));
    setText("ar-total-net", currency(summary.net_receivables_cents || 0));


    setHtml(
        "ar-customers-body",
        customers.length
            ? customers.map((customer) => `
                <tr class="transition hover:bg-white/70 ${customer.id === reportState.selectedCustomerId ? "bg-brand/10" : ""}">
                    <td class="px-4 py-2">
                        <button class="text-left" data-customer-report-id="${customer.id}" type="button">
                            <p class="font-semibold text-ink">${escapeHtml(customer.customer_name)}</p>
                            <p class="mt-1 text-xs text-muted">${escapeHtml(customer.contact_name)} · ${escapeHtml(customer.email)}</p>
                        </button>
                    </td>
                    <td class="px-4 py-2 font-mono text-sm">${currency(customer.open_ar_cents)}</td>
                    <td class="px-4 py-2 font-mono text-sm">${currency(customer.unapplied_credit_cents)}</td>
                    <td class="px-4 py-2 font-mono text-sm">${currency(customer.net_balance_cents)}</td>
                    <td class="px-4 py-2 text-sm text-muted">${customer.open_invoice_count}</td>
                </tr>`).join("")
            : '<tr><td class="px-4 py-2 text-muted" colspan="5">No customer balance activity is available.</td></tr>'
    );

    if (!statement || !statement.customer) {
        setText("statement-customer-name", "No statement available");
        setText("statement-customer-meta", "Select a customer with current balance activity to review statement detail.");
        setText("statement-open-ar", "-");
        setText("statement-unapplied-credit", "-");
        setText("statement-net-balance", "-");
        setText("statement-generated-at", "-");
        setHtml("statement-invoices-list", '<p class="rounded border border-line/80 bg-panel/35 px-4 py-2 text-sm text-muted">No printed invoices are available for this customer.</p>');
        setHtml("statement-payments-list", '<p class="rounded border border-line/80 bg-panel/35 px-4 py-2 text-sm text-muted">No unapplied payments are available for this customer.</p>');
        return;
    }

    setText("statement-customer-name", statement.customer.customer_name);
    setText(
        "statement-customer-meta",
        `${customerAddress(statement.customer)}${statement.customer.phone ? ` · ${statement.customer.phone}` : ""}${statement.customer.notes ? ` · ${statement.customer.notes}` : ""}`
    );
    setText("statement-open-ar", currency(statement.totals?.open_ar_cents || 0));
    setText("statement-unapplied-credit", currency(statement.totals?.unapplied_credit_cents || 0));
    setText("statement-net-balance", currency(statement.totals?.net_balance_cents || 0));
    setText("statement-generated-at", statementTimestamp(statement.generated_at));
    setHtml(
        "statement-invoices-list",
        Array.isArray(statement.invoices) && statement.invoices.length
            ? statement.invoices.map((invoice) => `
                <article class="rounded border border-line/80 bg-panel/35 px-4 py-2">
                    <div class="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <p class="font-display text-lg font-bold text-ink">${escapeHtml(invoice.invoice_number)}</p>
                            <p class="mt-1 text-sm text-muted">${escapeHtml(invoice.project_number)} · ${escapeHtml(invoice.invoice_date)}</p>
                        </div>
                        <div class="text-right">
                            <p class="font-mono text-sm text-ink">${currency(invoice.invoice_amount_cents)}</p>
                            <p class="mt-1 text-xs uppercase tracking-wide text-muted">${escapeHtml(invoice.status)}</p>
                        </div>
                    </div>
                    <div class="mt-3 flex flex-wrap gap-3 text-xs text-muted">
                        <span>Paid ${currency(invoice.paid_amount_cents)}</span>
                        <span>Open ${currency(invoice.open_balance_cents)}</span>
                        <span>Credit ${currency(invoice.unapplied_credit_cents)}</span>
                    </div>
                </article>`).join("")
            : '<p class="rounded border border-line/80 bg-panel/35 px-4 py-2 text-sm text-muted">No printed invoices are available for this customer.</p>'
    );
    setHtml(
        "statement-payments-list",
        Array.isArray(statement.unapplied_payments) && statement.unapplied_payments.length
            ? statement.unapplied_payments.map((payment) => `
                <article class="rounded border border-line/80 bg-panel/35 px-4 py-2">
                    <div class="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <p class="font-display text-lg font-bold text-ink">${escapeHtml(payment.reference_number || `Payment ${payment.id}`)}</p>
                            <p class="mt-1 text-sm text-muted">${escapeHtml(payment.payment_date)}</p>
                        </div>
                        <div class="text-right">
                            <p class="font-mono text-sm text-ink">${currency(payment.unapplied_amount_cents)}</p>
                            <p class="mt-1 text-xs text-muted">unapplied</p>
                        </div>
                    </div>
                </article>`).join("")
            : '<p class="rounded border border-line/80 bg-panel/35 px-4 py-2 text-sm text-muted">No unapplied payments are available for this customer.</p>'
    );
}

function renderAccountsReceivableError(message) {
    setText("ar-total-open", "-");
    setText("ar-total-credit", "-");
    setText("ar-total-net", "-");
    setHtml("ar-customers-body", `<tr><td class="px-4 py-2 text-muted" colspan="5">${escapeHtml(message)}</td></tr>`);
    setText("statement-customer-name", "Load Error");
    setText("statement-customer-meta", message);
    setText("statement-open-ar", "-");
    setText("statement-unapplied-credit", "-");
    setText("statement-net-balance", "-");
    setText("statement-generated-at", "-");
    setHtml("statement-invoices-list", '<p class="rounded border border-line/80 bg-panel/35 px-4 py-2 text-sm text-muted">Statement data could not be loaded.</p>');
    setHtml("statement-payments-list", '<p class="rounded border border-line/80 bg-panel/35 px-4 py-2 text-sm text-muted">Statement data could not be loaded.</p>');
}

async function loadOverview() {
    try {
        const response = await fetch("/api/overview/bootstrap", {
            headers: { Accept: "application/json" }
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.detail || payload.message || "Unable to load overview.");
        }
        renderOverview(payload.data || {});
    } catch (error) {
        renderOverviewError(error.message || "Unable to load overview.");
    }
}

async function loadAccountsReceivable(customerId = null) {
    const query = customerId ? `?customer_id=${encodeURIComponent(String(customerId))}` : "";
    try {
        const response = await fetch(`/api/reports/accounts-receivable${query}`, {
            headers: { Accept: "application/json" }
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.detail || payload.message || "Unable to load accounts receivable report.");
        }
        const data = payload.data || {};
        reportState.summary = data.summary || {};
        reportState.customers = Array.isArray(data.customers) ? data.customers : [];
        reportState.selectedCustomerId = data.selected_customer_id || null;
        reportState.statement = data.statement || null;
        renderAccountsReceivable();
    } catch (error) {
        renderAccountsReceivableError(error.message || "Unable to load accounts receivable report.");
    }
}

function bindReportingEvents() {
    document.getElementById("ar-customers-body")?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-customer-report-id]");
        if (!button) {
            return;
        }
        void loadAccountsReceivable(button.dataset.customerReportId || null);
    });

}

function bootstrapLandingPage() {
    bindReportingEvents();
    loadOverview();
    loadAccountsReceivable();
}

window.addEventListener("DOMContentLoaded", () => {
    bootstrapLandingPage();
});
