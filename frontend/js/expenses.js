const expensesState = {
    customers: [],
    projects: [],
    expenses: [],
    categories: [],
    searchQuery: "",
    statusFilter: "all",
    projectFilter: "all",
    yearFilter: "all",
    categoryFilter: "all",
    selectedId: null,
    draftExpense: null,
    isLoading: true,
    isSaving: false,
    loadError: ""
};

function expensesUrl(path = "") {
    return `/api/expenses${path}`;
}

function currency(cents) {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format((cents || 0) / 100);
}

function quantityLabel(quantity) {
    const numericQuantity = Number(quantity || 0);
    return numericQuantity.toFixed(numericQuantity % 1 === 0 ? 0 : 2);
}

function dollarsInput(cents) {
    return ((cents || 0) / 100).toFixed(2);
}

function centsFromInput(value) {
    return Math.round(Number(value || 0) * 100);
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (!element) {
        return;
    }
    element.textContent = value;
}

function getCurrentPage() {
    return window.location.pathname.split("/").pop() || "expenses.html";
}

function setEmptyState(message) {
    const element = document.getElementById("expense-empty-state");
    if (!element) {
        return;
    }
    element.textContent = message;
}

function extractErrorMessage(error, fallbackMessage) {
    if (!error) {
        return fallbackMessage;
    }
    if (typeof error === "string") {
        return error;
    }
    if (error.detail) {
        if (typeof error.detail === "string") {
            return error.detail;
        }
        if (Array.isArray(error.detail)) {
            return error.detail.map((item) => item.msg || item.message || String(item)).join(" ");
        }
    }
    if (error.message) {
        return error.message;
    }
    return fallbackMessage;
}

function projectById(projectId) {
    return expensesState.projects.find((project) => project.id === Number(projectId)) || null;
}

function expenseStatusMeta(expense) {
    if (expense.invoice_number) {
        return { label: "Invoiced", classes: "bg-calm/10 text-calm border border-calm/20" };
    }
    if (!expense.is_billable) {
        return { label: "Non-Billable", classes: "bg-stone-200/70 text-stone-700 border border-stone-300" };
    }
    return { label: "Unbilled", classes: "bg-brand/10 text-brand border border-brand/20" };
}

function emptyExpenseDraft(overrides = {}) {
    const firstProject = expensesState.projects[0];
    const firstCategory = expensesState.categories[0];
    return {
        id: "",
        entry_date: "2026-05-31",
        project_id: firstProject?.id || "",
        project_number: firstProject?.project_number || "",
        customer_id: firstProject?.customer_id || "",
        customer_name: firstProject?.customer_name || "",
        vendor: "",
        description: "",
        quantity: 1,
        unit_cost_cents: 0,
        line_total_cents: 0,
        category: firstCategory || "",
        is_billable: true,
        invoice_number: null,
        updated_at: new Date().toISOString(),
        ...overrides
    };
}

function selectedExpense() {
    return expensesState.expenses.find((expense) => expense.id === expensesState.selectedId) || null;
}

function upsertExpense(expense) {
    const index = expensesState.expenses.findIndex((currentExpense) => currentExpense.id === expense.id);
    if (index >= 0) {
        expensesState.expenses.splice(index, 1, expense);
    } else {
        expensesState.expenses.unshift(expense);
    }
    if (expense.category && !expensesState.categories.includes(expense.category)) {
        expensesState.categories.push(expense.category);
        expensesState.categories.sort((left, right) => left.localeCompare(right));
    }
}

async function loadExpenses() {
    expensesState.isLoading = true;
    expensesState.loadError = "";
    render();

    try {
        const response = await fetch(expensesUrl("/bootstrap"), {
            headers: { Accept: "application/json" }
        });
        const payload = await response.json();
        if (!response.ok) {
            throw payload;
        }
        const data = payload.data || {};
        expensesState.customers = Array.isArray(data.customers) ? data.customers : [];
        expensesState.projects = Array.isArray(data.projects) ? data.projects : [];
        expensesState.expenses = Array.isArray(data.expenses) ? data.expenses : [];
        expensesState.categories = Array.isArray(data.categories) ? data.categories : [];
        expensesState.selectedId = expensesState.expenses[0]?.id || null;
        expensesState.draftExpense = null;
    } catch (error) {
        expensesState.loadError = extractErrorMessage(error, "Unable to load expenses.");
        expensesState.expenses = [];
        expensesState.selectedId = null;
        expensesState.draftExpense = null;
    } finally {
        expensesState.isLoading = false;
        render();
    }
}

function filteredExpenses() {
    const query = expensesState.searchQuery.trim().toLowerCase();
    return expensesState.expenses.filter((expense) => {
        const status = expense.invoice_number ? "invoiced" : (expense.is_billable ? "unbilled" : "nonbillable");
        const matchesStatus = expensesState.statusFilter === "all" || status === expensesState.statusFilter;
        const matchesProject = expensesState.projectFilter === "all" || String(expense.project_id) === expensesState.projectFilter;
        const expenseYear = String(expense.entry_date).slice(0, 4);
        const matchesYear = expensesState.yearFilter === "all" || expenseYear === expensesState.yearFilter;
        const matchesCategory = expensesState.categoryFilter === "all" || expense.category === expensesState.categoryFilter;
        const haystack = [expense.project_number, expense.customer_name, expense.vendor, expense.description, expense.category, expense.invoice_number || ""].join(" ").toLowerCase();
        const matchesQuery = !query || haystack.includes(query);
        return matchesStatus && matchesProject && matchesYear && matchesCategory && matchesQuery;
    });
}

function renderNavState() {
    const currentPage = getCurrentPage();
    document.querySelectorAll(".side-nav .nav-link").forEach((link) => {
        const href = link.getAttribute("href") || "";
        const isPageLink = href.endsWith(".html");
        const targetPage = href.replace("./", "");
        const isActive = isPageLink && currentPage === targetPage;
        link.classList.toggle("bg-white/10", !isActive);
        link.classList.toggle("border-white/10", !isActive);
        link.classList.toggle("text-stone-100", !isActive);
        link.classList.toggle("bg-gradient-to-r", isActive);
        link.classList.toggle("from-sand/35", isActive);
        link.classList.toggle("to-brand/35", isActive);
        link.classList.toggle("border-sand/50", isActive);
        link.classList.toggle("text-white", isActive);
        link.classList.toggle("shadow-lg", isActive);
    });
}

function renderProjectOptions() {
    const filter = document.getElementById("expense-project-filter");
    const editor = document.getElementById("expense-project");
    if (!filter || !editor) {
        return;
    }
    filter.innerHTML = ['<option value="all">All Projects</option>', ...expensesState.projects.map((project) => `<option value="${project.id}">${project.project_number} · ${project.customer_name}</option>`)].join("");
    filter.value = expensesState.projectFilter;
    editor.innerHTML = expensesState.projects.map((project) => `<option value="${project.id}">${project.project_number} · ${project.customer_name}</option>`).join("");
}

function renderYearOptions() {
    const filter = document.getElementById("expense-year-filter");
    if (!filter) {
        return;
    }
    const years = Array.from(new Set(expensesState.expenses.map((expense) => String(expense.entry_date).slice(0, 4)))).sort().reverse();
    filter.innerHTML = ['<option value="all">All Years</option>', ...years.map((year) => `<option value="${year}">${year}</option>`)].join("");
    filter.value = expensesState.yearFilter;
}

function renderCategoryOptions() {
    const filter = document.getElementById("expense-category-filter");
    const editor = document.getElementById("expense-category");
    if (!filter || !editor) {
        return;
    }
    filter.innerHTML = ['<option value="all">All Categories</option>', ...expensesState.categories.map((category) => `<option value="${category}">${category}</option>`)].join("");
    filter.value = expensesState.categoryFilter;
    editor.innerHTML = expensesState.categories.map((category) => `<option value="${category}">${category}</option>`).join("");
}

function renderMetrics(expenses) {
    const visibleSpend = expenses.reduce((sum, expense) => sum + expense.line_total_cents, 0);
    const billableUnbilled = expenses.reduce((sum, expense) => sum + (!expense.invoice_number && expense.is_billable ? expense.line_total_cents : 0), 0);
    const invoicedSpend = expenses.reduce((sum, expense) => sum + (expense.invoice_number ? expense.line_total_cents : 0), 0);
    const nonbillableSpend = expenses.reduce((sum, expense) => sum + (!expense.is_billable ? expense.line_total_cents : 0), 0);
    setText("expenses-mode", expensesState.isLoading ? "Loading" : "Served Mode");
    setText("metric-visible-spend", currency(visibleSpend));
    setText("metric-billable-unbilled", currency(billableUnbilled));
    setText("metric-invoiced-spend", currency(invoicedSpend));
    setText("metric-nonbillable-spend", currency(nonbillableSpend));
}

function renderStatusFilters() {
    document.querySelectorAll("[data-expense-status-filter]").forEach((button) => {
        const isActive = button.dataset.expenseStatusFilter === expensesState.statusFilter;
        button.classList.toggle("bg-brand", isActive);
        button.classList.toggle("text-stone-50", isActive);
        button.classList.toggle("border-brand", isActive);
        button.classList.toggle("shadow-sm", isActive);
        button.classList.toggle("bg-panel/70", !isActive);
        button.classList.toggle("text-ink", !isActive);
        button.classList.toggle("border-line", !isActive);
    });
}

function renderExpenseRows(expenses) {
    const tbody = document.getElementById("expense-table-body");
    const emptyState = document.getElementById("expense-empty-state");
    if (!tbody || !emptyState) {
        return;
    }
    if (expensesState.isLoading) {
        tbody.innerHTML = "";
        setEmptyState("Loading expenses...");
        emptyState.classList.remove("hidden");
        return;
    }
    if (expensesState.loadError) {
        tbody.innerHTML = "";
        setEmptyState(expensesState.loadError);
        emptyState.classList.remove("hidden");
        return;
    }
    if (expenses.length === 0) {
        tbody.innerHTML = "";
        setEmptyState("No expenses match the current filters.");
        emptyState.classList.remove("hidden");
        return;
    }
    emptyState.classList.add("hidden");
    tbody.innerHTML = expenses.map((expense) => {
        const status = expenseStatusMeta(expense);
        const isSelected = expense.id === expensesState.selectedId;
        return `
            <tr class="cursor-pointer border-t border-line/70 ${isSelected ? "bg-brand/5" : "bg-white/30 hover:bg-white/60"}" data-expense-select="${expense.id}">
                <td class="px-4 py-4 align-top font-mono text-sm text-ink">${expense.entry_date}</td>
                <td class="px-4 py-4 align-top text-sm text-ink">${expense.project_number}</td>
                <td class="px-4 py-4 align-top text-sm text-ink">${expense.vendor}</td>
                <td class="px-4 py-4 align-top text-sm text-muted">${expense.description}</td>
                <td class="px-4 py-4 align-top text-sm text-ink">${expense.category}</td>
                <td class="px-4 py-4 align-top text-right font-mono text-sm text-ink">${currency(expense.line_total_cents)}</td>
                <td class="px-4 py-4 align-top"><span class="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${status.classes}">${status.label}</span></td>
            </tr>
        `;
    }).join("");
    tbody.querySelectorAll("[data-expense-select]").forEach((row) => {
        row.addEventListener("click", () => {
            expensesState.selectedId = Number(row.dataset.expenseSelect);
            expensesState.draftExpense = null;
            render();
        });
    });
}

function updateDerivedPreview(expense) {
    const statusChip = document.getElementById("expense-editor-status-chip");
    if (!expense) {
        return;
    }
    const status = expenseStatusMeta(expense);
    if (statusChip) {
        statusChip.className = `rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${status.classes}`;
        statusChip.textContent = expense.id ? status.label : "Draft";
    }
    const derivedLabel = !expense.is_billable
        ? "Non-billable: this cost remains tracked against the project but stays out of invoice selection."
        : expense.invoice_number
            ? `Invoiced on ${expense.invoice_number}. This cost keeps its source linkage.`
            : `Billable: this cost is eligible for invoice selection and currently unbilled.`;
    setText("expense-editor-title", expense.id ? `Expense ${expense.entry_date}` : "New Expense Draft");
    setText("expense-detail-customer", expense.customer_name || "None");
    setText("expense-detail-total", currency(expense.line_total_cents));
    setText("expense-detail-invoice", expense.invoice_number || "Not linked");
    setText("expense-derived-billing", `${derivedLabel} Quantity ${quantityLabel(expense.quantity)} at ${currency(expense.unit_cost_cents)} each.`);
}

function renderEditor(expense) {
    const form = document.getElementById("expense-form");
    if (!form) {
        return;
    }
    const current = expense || emptyExpenseDraft();
    document.getElementById("expense-entry-id").value = current.id;
    document.getElementById("expense-entry-date").value = current.entry_date;
    document.getElementById("expense-project").value = String(current.project_id || "");
    document.getElementById("expense-vendor").value = current.vendor;
    document.getElementById("expense-category").value = current.category;
    document.getElementById("expense-description").value = current.description;
    document.getElementById("expense-quantity").value = current.quantity;
    document.getElementById("expense-unit-cost").value = dollarsInput(current.unit_cost_cents);
    document.getElementById("expense-is-billable").checked = current.is_billable;
    updateDerivedPreview(current);
}

function syncDraftFromForm() {
    const projectId = Number(document.getElementById("expense-project")?.value || 0);
    const project = projectById(projectId);
    const quantity = Number(document.getElementById("expense-quantity")?.value || 0);
    const unitCostCents = centsFromInput(document.getElementById("expense-unit-cost")?.value || 0);
    const source = expensesState.draftExpense || selectedExpense() || emptyExpenseDraft();
    expensesState.draftExpense = {
        ...source,
        entry_date: String(document.getElementById("expense-entry-date")?.value || source.entry_date),
        project_id: projectId,
        project_number: project?.project_number || source.project_number,
        customer_id: project?.customer_id || source.customer_id,
        customer_name: project?.customer_name || source.customer_name,
        vendor: String(document.getElementById("expense-vendor")?.value || source.vendor),
        description: String(document.getElementById("expense-description")?.value || source.description),
        quantity: quantity || 0,
        unit_cost_cents: unitCostCents,
        line_total_cents: Math.round(quantity * unitCostCents),
        category: String(document.getElementById("expense-category")?.value || source.category),
        is_billable: Boolean(document.getElementById("expense-is-billable")?.checked),
        invoice_number: source.invoice_number,
        updated_at: new Date().toISOString()
    };
    updateDerivedPreview(expensesState.draftExpense);
}

async function saveExpense(event) {
    event.preventDefault();
    if (expensesState.isSaving) {
        return;
    }
    syncDraftFromForm();
    const draft = expensesState.draftExpense || emptyExpenseDraft();
    const payload = {
        entry_date: draft.entry_date,
        project_id: Number(draft.project_id),
        vendor: draft.vendor,
        description: draft.description,
        quantity: Number(draft.quantity),
        unit_cost_cents: Number(draft.unit_cost_cents),
        category: draft.category,
        is_billable: Boolean(draft.is_billable)
    };

    const expenseId = Number(document.getElementById("expense-entry-id")?.value || 0);
    const method = expenseId ? "PUT" : "POST";
    const path = expenseId ? `/${expenseId}` : "";

    expensesState.isSaving = true;
    render();
    try {
        const response = await fetch(expensesUrl(path), {
            method,
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json"
            },
            body: JSON.stringify(payload)
        });
        const responsePayload = await response.json();
        if (!response.ok) {
            throw responsePayload;
        }
        const saved = responsePayload.data?.expense;
        if (!saved) {
            throw new Error("Expense response was missing the saved record.");
        }
        upsertExpense(saved);
        expensesState.selectedId = saved.id;
        expensesState.draftExpense = null;
        expensesState.loadError = "";
    } catch (error) {
        expensesState.loadError = extractErrorMessage(error, "Unable to save expense.");
    } finally {
        expensesState.isSaving = false;
        render();
    }
}

function clearExpenseDraft(copyCurrent = false) {
    if (copyCurrent && selectedExpense()) {
        const original = selectedExpense();
        expensesState.selectedId = null;
        expensesState.draftExpense = emptyExpenseDraft({
            entry_date: original.entry_date,
            project_id: original.project_id,
            project_number: original.project_number,
            customer_id: original.customer_id,
            customer_name: original.customer_name,
            vendor: original.vendor,
            description: original.description,
            quantity: original.quantity,
            unit_cost_cents: original.unit_cost_cents,
            line_total_cents: original.line_total_cents,
            category: original.category,
            is_billable: original.is_billable
        });
        render();
        return;
    }
    expensesState.selectedId = null;
    expensesState.draftExpense = emptyExpenseDraft();
    render();
}

function bindEvents() {
    document.getElementById("expense-search")?.addEventListener("input", (event) => {
        expensesState.searchQuery = event.target.value;
        render();
    });
    document.getElementById("expense-project-filter")?.addEventListener("change", (event) => {
        expensesState.projectFilter = event.target.value;
        render();
    });
    document.getElementById("expense-year-filter")?.addEventListener("change", (event) => {
        expensesState.yearFilter = event.target.value;
        render();
    });
    document.getElementById("expense-category-filter")?.addEventListener("change", (event) => {
        expensesState.categoryFilter = event.target.value;
        render();
    });
    document.querySelectorAll("[data-expense-status-filter]").forEach((button) => {
        button.addEventListener("click", () => {
            expensesState.statusFilter = button.dataset.expenseStatusFilter || "all";
            render();
        });
    });
    document.getElementById("expense-form")?.addEventListener("submit", saveExpense);
    document.getElementById("new-expense-button")?.addEventListener("click", () => clearExpenseDraft(false));
    document.getElementById("clear-expense-form-button")?.addEventListener("click", () => clearExpenseDraft(false));
    document.getElementById("duplicate-expense-button")?.addEventListener("click", () => clearExpenseDraft(true));
    document.getElementById("reset-expense-filters-button")?.addEventListener("click", () => {
        expensesState.searchQuery = "";
        expensesState.projectFilter = "all";
        expensesState.yearFilter = "all";
        expensesState.categoryFilter = "all";
        expensesState.statusFilter = "all";
        const search = document.getElementById("expense-search");
        if (search) {
            search.value = "";
        }
        render();
    });
    document.getElementById("expense-project")?.addEventListener("change", syncDraftFromForm);
    document.getElementById("expense-entry-date")?.addEventListener("input", syncDraftFromForm);
    document.getElementById("expense-vendor")?.addEventListener("input", syncDraftFromForm);
    document.getElementById("expense-category")?.addEventListener("change", syncDraftFromForm);
    document.getElementById("expense-description")?.addEventListener("input", syncDraftFromForm);
    document.getElementById("expense-quantity")?.addEventListener("input", syncDraftFromForm);
    document.getElementById("expense-unit-cost")?.addEventListener("input", syncDraftFromForm);
    document.getElementById("expense-is-billable")?.addEventListener("change", syncDraftFromForm);
}

function render() {
    renderNavState();
    renderProjectOptions();
    renderYearOptions();
    renderCategoryOptions();
    renderStatusFilters();
    const expenses = filteredExpenses();
    renderMetrics(expenses);
    renderExpenseRows(expenses);
    const expense = selectedExpense() || expensesState.draftExpense || emptyExpenseDraft();
    renderEditor(expense);
}

window.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    render();
    loadExpenses();
});