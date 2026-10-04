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

    if (state.isSaving) {
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
    } catch (error) {
        showToast(error instanceof Error ? error.message : "Unable to save customer.");
    } finally {
        state.isSaving = false;
    }

    render();
}

function clearFormToDraft(copyCurrent = false) {
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
        return;
    }

    state.selectedId = null;
    state.draftCustomer = blankCustomerDraft();
    render();
}

function bindEvents() {
    document.getElementById("customer-table-body")?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-customer-select]");
        if (!button) return;
        state.selectedId = Number(button.dataset.customerSelect);
        state.draftCustomer = null;
        render();
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

    const customer = selectedCustomer() || state.draftCustomer;
    renderEditor(customer);
}

window.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    render();
    void loadCustomers().then(() => consumeNewRecordRequest("new-customer-button"));
});
