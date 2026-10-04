/**
 * @fileoverview Browse, filter, and edit customer records.
 * @license Apache-2.0
 * @copyright 2026 Timothy Mallory
 */

const state = {
    customers: [],
    searchQuery: "",
    statusFilter: "all",
    selectedId: null,
    draftCustomer: null,
    isLoading: true,
    isSaving: false,
    loadError: ""
};

const customerStatement = { customerId: undefined, request: 0, data: null, loading: false, error: "", tab: "contact" };

function renderCustomerTabs() {
    document.querySelectorAll("[data-customer-tab]").forEach((button) => {
        button.setAttribute("aria-selected", String(button.dataset.customerTab === customerStatement.tab));
        button.setAttribute("aria-pressed", String(button.dataset.customerTab === customerStatement.tab));
        button.tabIndex = button.dataset.customerTab === customerStatement.tab ? 0 : -1;
    });
    document.getElementById("customer-contact-panel").hidden = customerStatement.tab !== "contact";
    document.getElementById("customer-statement-panel").hidden = customerStatement.tab !== "statement";
}

async function loadCustomerStatement(force = false) {
    const id = state.selectedId;
    if (!force && customerStatement.customerId === id) return;
    const request = ++customerStatement.request;
    customerStatement.customerId = id;
    customerStatement.data = null;
    customerStatement.error = "";
    customerStatement.loading = Boolean(id);
    renderCustomerStatement();
    if (!id) return;
    try {
        const data = await apiRequestJson("/api/reports/accounts-receivable", `?customer_id=${id}`, {}, "Unable to load customer statement.");
        if (request !== customerStatement.request || state.selectedId !== id) return;
        customerStatement.data = data.statement;
    } catch (error) {
        if (request !== customerStatement.request) return;
        customerStatement.error = extractErrorMessage(error, "Unable to load customer statement.");
    } finally {
        if (request === customerStatement.request) {
            customerStatement.loading = false;
            renderCustomerStatement();
        }
    }
}

function renderCustomerStatement() {
    const statement = customerStatement.data;
    const message = customerStatement.loading ? "Loading statement..." : customerStatement.error ||
        (!state.selectedId ? "Save the new customer to view its statement." : !statement ? "No statement available." : "");
    setText("statement-message", message);
    document.getElementById("statement-detail").hidden = Boolean(message);
    if (message || !statement) return;
    const customer = statement.customer;
    setText("statement-customer-name", customer.customer_name);
    setText("statement-customer-meta", [customer.contact_name, customer.email, customer.phone,
        customer.street_address, [customer.city, customer.state, customer.zip].filter(Boolean).join(" "), customer.notes].filter(Boolean).join(" · "));
    setText("statement-open-ar", currency(statement.totals?.open_ar_cents));
    setText("statement-unapplied-credit", currency(statement.totals?.unapplied_credit_cents));
    setText("statement-net-balance", currency(statement.totals?.net_balance_cents));
    const generated = new Date(statement.generated_at);
    setText("statement-generated-at", Number.isNaN(generated.getTime()) ? "" : `Generated ${generated.toLocaleString()}`);
    setHtml("statement-invoices-list", (statement.invoices || []).map((invoice) => {
        const status = invoiceDisplayStatus(invoice);
        return `<article class="rounded border border-line bg-panel/35 p-3">
            <div class="flex flex-wrap justify-between gap-2"><strong>${escapeHtml(invoice.invoice_number)}</strong><span class="badge ${status.classes}">${status.label}</span></div>
            <p class="mt-1 text-xs text-muted">${escapeHtml(invoice.project_number)} · ${escapeHtml(invoice.invoice_date)} · Due ${escapeHtml(invoiceDueDate(invoice))}</p>
            <div class="mt-2 flex flex-wrap gap-3 text-xs"><span>Amount ${currency(invoice.invoice_amount_cents)}</span><span>Paid ${currency(invoice.paid_amount_cents)}</span><span>Open ${currency(invoice.open_balance_cents)}</span></div>
        </article>`;
    }).join("") || '<p class="text-sm text-muted">No issued invoices for this customer.</p>');
    setHtml("statement-payments-list", (statement.unapplied_payments || []).map((payment) =>
        `<article class="rounded border border-line bg-panel/35 p-3"><div class="flex justify-between gap-2"><strong>${escapeHtml(payment.reference_number || `Payment ${payment.id}`)}</strong><span class="font-mono">${currency(payment.unapplied_amount_cents)}</span></div><p class="mt-1 text-xs text-muted">${escapeHtml(payment.payment_date)} · Unapplied credit</p></article>`
    ).join("") || '<p class="text-sm text-muted">No unapplied payments for this customer.</p>');
}

function customersUrl(path = "") {
    return `/api/customers${path}`;
}

function blankCustomerDraft(overrides = {}) {
    return {
        id: "",
        customer_name: "",
        contact_name: "",
        email: "",
        phone: "",
        street_address: "",
        city: "",
        state: "",
        zip: "",
        notes: "",
        open_ar_cents: 0,
        net_balance_cents: 0,
        ...overrides
    };
}

function setEmptyState(title, message) {
    const emptyState = document.getElementById("empty-state");
    if (!emptyState) {
        return;
    }

    emptyState.innerHTML = `
        <p class="font-display text-lg font-semibold text-ink">${escapeHtml(title)}</p>
        <p class="mt-2 text-sm leading-6 text-muted">${escapeHtml(message)}</p>
    `;
}

function upsertCustomer(customer) {
    const existingIndex = state.customers.findIndex((entry) => entry.id === customer.id);
    if (existingIndex >= 0) {
        state.customers.splice(existingIndex, 1, customer);
        return;
    }

    state.customers.unshift(customer);
}

async function loadCustomers() {
    state.isLoading = true;
    state.loadError = "";
    render();

    try {
        const response = await fetch(customersUrl("/bootstrap"));
        const payload = await response.json();

        if (!response.ok) {
            throw new Error(extractErrorMessage(payload, "Unable to load customers."));
        }

        state.customers = Array.isArray(payload?.data?.customers) ? payload.data.customers : [];

        if (state.selectedId && !state.customers.some((customer) => customer.id === state.selectedId)) {
            state.selectedId = null;
        }

        if (!state.selectedId && state.customers.length > 0) {
            state.selectedId = state.customers[0].id;
        }
    } catch (error) {
        state.customers = [];
        state.selectedId = null;
        state.loadError = error instanceof Error ? error.message : "Unable to load customers.";
    } finally {
        state.isLoading = false;
        render();
    }
}

function getStatusMeta(customer) {
    const netBalance = customer.net_balance_cents || 0;

    if (netBalance > 0) {
        return {
            label: "Open Balance",
            filterValue: "open",
            classes: "bg-warn/10 text-warn border border-warn/20"
        };
    }

    if (netBalance < 0) {
        return {
            label: "Credit",
            filterValue: "credit",
            classes: "bg-calm/10 text-calm border border-calm/20"
        };
    }

    return {
        label: "Clear",
        filterValue: "clear",
        classes: "bg-brand/10 text-brand border border-brand/20"
    };
}

function filteredCustomers() {
    const query = state.searchQuery.trim().toLowerCase();

    return state.customers.filter((customer) => {
        const statusMeta = getStatusMeta(customer);
        const matchesStatus = state.statusFilter === "all" || statusMeta.filterValue === state.statusFilter;
        const haystack = [
            customer.customer_name,
            customer.contact_name,
            customer.email,
            customer.phone,
            customer.city,
            customer.state
        ].join(" ").toLowerCase();
        const matchesQuery = !query || haystack.includes(query);

        return matchesStatus && matchesQuery;
    });
}

function selectedCustomer() {
    return state.customers.find((customer) => customer.id === state.selectedId) || null;
}

function renderMetrics(customers) {
    if (state.isLoading) {

        setText("metric-visible-customers", "-");
        setText("metric-open-ar", "-");
        setText("metric-net-balance", "-");
        setText("metric-with-balance", "-");
        return;
    }

    const openAr = customers.reduce((sum, customer) => sum + customer.open_ar_cents, 0);
    const netBalance = customers.reduce((sum, customer) => sum + customer.net_balance_cents, 0);
    const customersWithBalance = customers.filter((customer) => customer.net_balance_cents !== 0).length;

    setText("metric-visible-customers", String(customers.length));
    setText("metric-open-ar", formatCurrency(openAr));
    setText("metric-net-balance", formatCurrency(netBalance));
    setText("metric-with-balance", String(customersWithBalance));
}

function renderStatusFilters() {
    syncFilterButtons("[data-status-filter]", "data-status-filter", state.statusFilter);
}

function renderCustomerRows(customers) {
    const list = document.getElementById("customer-table-body");
    const emptyState = document.getElementById("empty-state");
    if (!list || !emptyState) {
        return;
    }

    if (state.isLoading) {
        list.innerHTML = "";
        setEmptyState("Loading customers...", "The customer screen is waiting for the bootstrap payload from the API.");
        emptyState.classList.remove("hidden");
        return;
    }

    if (state.loadError) {
        list.innerHTML = "";
        setEmptyState("Customer load failed", state.loadError);
        emptyState.classList.remove("hidden");
        return;
    }

    if (customers.length === 0) {
        list.innerHTML = "";
        setEmptyState("No customers match the current filter.", "Try a different balance filter, clear the search, or create a new customer draft.");
        emptyState.classList.remove("hidden");
        return;
    }

    emptyState.classList.add("hidden");
    list.innerHTML = customers.map((customer) => {
        const status = getStatusMeta(customer);
        return `<tr class="${customer.id === state.selectedId ? "bg-brand/5" : ""}">
            <td><button class="text-left font-semibold text-brand hover:underline" data-customer-select="${customer.id}" type="button">${escapeHtml(customer.customer_name)}</button><div class="text-xs text-muted">${escapeHtml(customer.contact_name)}</div></td>
            <td>${escapeHtml(customer.phone)}</td><td>${escapeHtml(customer.email)}</td>
            <td>${escapeHtml(customer.city)}, ${escapeHtml(customer.state)}</td>
            <td class="text-right font-mono">${currency(customer.open_ar_cents)}</td>
            <td><span class="badge ${status.classes}">${escapeHtml(status.label)}</span></td></tr>`;
    }).join("");

}

function renderEditor(customer) {
    const form = document.getElementById("customer-form");
    if (!form) {
        return;
    }

    const current = customer || blankCustomerDraft();

    document.getElementById("customer-id").value = current.id;
    document.getElementById("customer-name").value = current.customer_name;
    document.getElementById("contact-name").value = current.contact_name;
    document.getElementById("email").value = current.email;
    document.getElementById("phone").value = current.phone;
    document.getElementById("street-address").value = current.street_address;
    document.getElementById("city").value = current.city;
    document.getElementById("state").value = current.state;
    document.getElementById("zip").value = current.zip;
    document.getElementById("notes").value = current.notes;

    setText("editor-title", current.customer_name || "New Customer Draft");
    setText("detail-open-ar", formatCurrency(current.open_ar_cents));
    setText("detail-net-balance", formatCurrency(current.net_balance_cents));

    const statusChip = document.getElementById("editor-status-chip");
    if (statusChip) {
        const statusMeta = getStatusMeta(current);
        statusChip.className = `rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${statusMeta.classes}`;
        statusChip.textContent = current.customer_name ? statusMeta.label : "Draft";
    }
}

async function saveCustomer(event) {
    event.preventDefault();

    if (state.isSaving || !editorProtection.canWrite()) {
        return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    const customerId = Number(formData.get("customer_id") || document.getElementById("customer-id").value || 0);

    const payload = {
        customer_name: String(formData.get("customer_name") || "").trim(),
        contact_name: String(formData.get("contact_name") || "").trim(),
        email: String(formData.get("email") || "").trim(),
        phone: String(formData.get("phone") || "").trim(),
        street_address: String(formData.get("street_address") || "").trim(),
        city: String(formData.get("city") || "").trim(),
        state: String(formData.get("state") || "").trim().toUpperCase(),
        zip: String(formData.get("zip") || "").trim(),
        notes: String(formData.get("notes") || "").trim()
    };

    const method = customerId ? "PUT" : "POST";
    const path = customerId ? `/${customerId}` : "";

    try {
        state.isSaving = true;
        editorProtection.refresh();
        const response = await fetch(customersUrl(path), {
            method,
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });
        const responseBody = await response.json();

        if (!response.ok) {
            throw new Error(extractErrorMessage(responseBody, "Unable to save customer."));
        }

        const customer = responseBody?.data?.customer;
        if (!customer) {
            throw new Error("Customer save completed without a returned record.");
        }

        upsertCustomer(customer);
        state.selectedId = customer.id;
        state.draftCustomer = null;
        render();
        editorProtection.saved();
        void loadCustomerStatement(true);
    } catch (error) {
        showToast(error instanceof Error ? error.message : "Unable to save customer.");
    } finally {
        state.isSaving = false;
    }

    render();
}

function clearFormToDraft(copyCurrent = false) {
    if (!editorProtection.allowTransition()) return;
    if (copyCurrent && selectedCustomer()) {
        const original = selectedCustomer();
        state.selectedId = null;
        state.draftCustomer = blankCustomerDraft({
            id: "",
            customer_name: `${original.customer_name} Copy`,
            contact_name: original.contact_name,
            email: original.email,
            phone: original.phone,
            street_address: original.street_address,
            city: original.city,
            state: original.state,
            zip: original.zip,
            notes: original.notes,
            open_ar_cents: 0,
            net_balance_cents: 0
        });
        render();
        editorProtection.accept({ lock: true, duplicate: copyCurrent });
        return;
    }

    state.selectedId = null;
    state.draftCustomer = blankCustomerDraft();
    render();
    editorProtection.accept({ lock: true, duplicate: copyCurrent });
}

function syncCustomerDraft() {
    if (!editorProtection.canWrite() || state.isSaving) return;
    const source = state.draftCustomer || selectedCustomer() || blankCustomerDraft();
    state.draftCustomer = { ...source };
    const fields = { customer_name: 'customer-name', contact_name: 'contact-name', email: 'email', phone: 'phone', street_address: 'street-address', city: 'city', state: 'state', zip: 'zip', notes: 'notes' };
    Object.entries(fields).forEach(([key, id]) => { state.draftCustomer[key] = document.getElementById(id).value; });
}

function bindEvents() {
    document.querySelectorAll("[data-customer-tab]").forEach((button) => button.addEventListener("click", () => {
        customerStatement.tab = button.dataset.customerTab;
        renderCustomerTabs();
    }));
    document.querySelectorAll("[data-customer-tab]").forEach((button) => button.addEventListener("keydown", (event) => {
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        customerStatement.tab = event.key === "Home" ? "contact" : event.key === "End" ? "statement" : customerStatement.tab === "contact" ? "statement" : "contact";
        renderCustomerTabs();
        document.querySelector(`[data-customer-tab="${customerStatement.tab}"]`).focus();
    }));
    document.getElementById("refresh-statement-button")?.addEventListener("click", () => void loadCustomerStatement(true));
    document.getElementById("customer-form")?.addEventListener("input", syncCustomerDraft);
    document.getElementById("customer-table-body")?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-customer-select]");
        if (!button) return;
        const nextId = Number(button.dataset.customerSelect);
        if (nextId === state.selectedId || !editorProtection.allowTransition()) return;
        state.selectedId = nextId;
        state.draftCustomer = null;
        render();
        editorProtection.accept();
    });
    document.getElementById("customer-search")?.addEventListener("input", (event) => {
        state.searchQuery = event.target.value;
        render();
    });

    document.querySelectorAll("[data-status-filter]").forEach((button) => {
        button.addEventListener("click", () => {
            state.statusFilter = button.dataset.statusFilter || "all";
            render();
        });
    });

    document.getElementById("customer-form")?.addEventListener("submit", saveCustomer);
    document.getElementById("new-customer-button")?.addEventListener("click", () => clearFormToDraft(false));
    document.getElementById("clear-form-button")?.addEventListener("click", () => clearFormToDraft(false));
    document.getElementById("duplicate-customer-button")?.addEventListener("click", () => clearFormToDraft(true));
    document.getElementById("reset-filters-button")?.addEventListener("click", () => {
        state.searchQuery = "";
        state.statusFilter = "all";
        const search = document.getElementById("customer-search");
        if (search) {
            search.value = "";
        }
        render();
    });
}

function render() {
    renderStatusFilters();

    const customers = filteredCustomers();
    renderMetrics(customers);
    renderCustomerRows(customers);

    const customer = state.draftCustomer || selectedCustomer();
    renderEditor(customer);
    editorProtection.refresh();
    renderCustomerTabs();
    void loadCustomerStatement();
}

window.addEventListener("DOMContentLoaded", () => {
    onInvoiceCalendarChange(renderCustomerStatement);
    editorProtection.register({
        formId: "customer-form",
        recordId: () => state.selectedId,
        busy: () => state.isLoading || state.isSaving,
        snapshot: () => editorFormSnapshot("customer-form"),
        capture: () => state.draftCustomer || selectedCustomer() || blankCustomerDraft(),
        restore: (record) => { state.draftCustomer = record; },
        render,
    });
    bindEvents();
    render();
    void loadCustomers().then(() => consumeNewRecordRequest("new-customer-button"));
});
