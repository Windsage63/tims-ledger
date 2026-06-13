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
        <p class="font-display text-2xl font-bold text-ink">${title}</p>
        <p class="mt-2 text-sm leading-6 text-muted">${message}</p>
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
        setText("customer-mode", "Loading...");
        setText("metric-visible-customers", "-");
        setText("metric-open-ar", "-");
        setText("metric-net-balance", "-");
        setText("metric-with-balance", "-");
        return;
    }

    const openAr = customers.reduce((sum, customer) => sum + customer.open_ar_cents, 0);
    const netBalance = customers.reduce((sum, customer) => sum + customer.net_balance_cents, 0);
    const customersWithBalance = customers.filter((customer) => customer.net_balance_cents !== 0).length;

    setText("customer-mode", window.location.protocol === "file:" ? "File Mode" : "SQLite Mode");
    setText("metric-visible-customers", String(customers.length));
    setText("metric-open-ar", formatCurrency(openAr));
    setText("metric-net-balance", formatCurrency(netBalance));
    setText("metric-with-balance", String(customersWithBalance));
}

function renderStatusFilters() {
    document.querySelectorAll("[data-status-filter]").forEach((button) => {
        const isActive = button.dataset.statusFilter === state.statusFilter;
        button.classList.toggle("bg-brand", isActive);
        button.classList.toggle("text-stone-50", isActive);
        button.classList.toggle("border-brand", isActive);
        button.classList.toggle("shadow-sm", isActive);
        button.classList.toggle("bg-panel/70", !isActive);
        button.classList.toggle("text-ink", !isActive);
        button.classList.toggle("border-line", !isActive);
    });
}

function renderCards(customers) {
    const list = document.getElementById("customer-card-list");
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
        const statusMeta = getStatusMeta(customer);
        const isSelected = customer.id === state.selectedId;

        return `
            <button class="text-left rounded-[1.35rem] border ${isSelected ? "border-brand bg-white shadow-soft" : "border-line bg-panel/35"} p-5 transition hover:-translate-y-0.5 hover:border-brand/35 hover:bg-white" data-customer-select="${customer.id}" type="button">
                <div class="flex items-start justify-between gap-4">
                    <div>
                        <p class="font-display text-xl font-bold text-ink">${customer.customer_name}</p>
                        <p class="mt-1 text-sm text-muted">${customer.contact_name}</p>
                    </div>
                    <span class="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${statusMeta.classes}">${statusMeta.label}</span>
                </div>
                <div class="mt-4 space-y-2 text-sm text-muted">
                    <p>${customer.email}</p>
                    <p>${customer.phone}</p>
                    <p>${customer.city}, ${customer.state}</p>
                </div>
                <div class="mt-5 grid grid-cols-2 gap-3 border-t border-line/70 pt-4 text-sm">
                    <div>
                        <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">Open A/R</p>
                        <p class="mt-1 font-mono text-ink">${formatCurrency(customer.open_ar_cents)}</p>
                    </div>
                    <div>
                        <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">Net Balance</p>
                        <p class="mt-1 font-mono text-ink">${formatCurrency(customer.net_balance_cents)}</p>
                    </div>
                </div>
            </button>
        `;
    }).join("");

    list.querySelectorAll("[data-customer-select]").forEach((button) => {
        button.addEventListener("click", () => {
            state.selectedId = Number(button.dataset.customerSelect);
            state.draftCustomer = null;
            render();
        });
    });
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
        window.alert(error instanceof Error ? error.message : "Unable to save customer.");
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
    renderNavState();
    renderStatusFilters();

    const customers = filteredCustomers();
    renderMetrics(customers);
    renderCards(customers);

    const customer = selectedCustomer() || state.draftCustomer;
    renderEditor(customer);
}

window.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    render();
    void loadCustomers();
});
