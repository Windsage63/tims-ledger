const TODAY = "2026-05-31";

const invoicesState = {
    projects: [],
    invoices: [],
    editor: {
        invoice: null,
        selected_time_entries: [],
        selected_expenses: [],
        eligible_time_entries: [],
        eligible_expenses: [],
        summary: {}
    },
    searchQuery: "",
    statusFilter: "all",
    yearFilter: "all",
    selectedInvoiceId: null,
    isLoading: true,
    isSaving: false,
    loadError: ""
};

function invoicesUrl(path = "") {
    return `/api/invoices${path}`;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function currency(cents) {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format((cents || 0) / 100);
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (!element) {
        return;
    }
    element.textContent = value;
}

function setEmptyState(message) {
    const element = document.getElementById("invoice-empty-state");
    if (!element) {
        return;
    }
    const heading = element.querySelector("p.font-display");
    const detail = element.querySelector("p.mt-2");
    if (heading) {
        heading.textContent = message;
    }
    if (detail) {
        detail.textContent = invoicesState.loadError ? "Retry after the API is available or correct the reported validation issue." : "Adjust the year or status filter, or create a new invoice.";
    }
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

function getCurrentPage() {
    return window.location.pathname.split("/").pop() || "invoices.html";
}

function projectById(projectId) {
    return invoicesState.projects.find((project) => project.id === Number(projectId)) || null;
}

function timeHours(minutes) {
    return ((minutes || 0) / 60).toFixed(2);
}

function deriveInvoiceStatus(invoice) {
    return invoice?.status || "draft";
}

function invoiceStatusMeta(invoice) {
    const status = deriveInvoiceStatus(invoice);
    if (status === "new") {
        return { key: status, label: "Unsaved", classes: "bg-calm/10 text-calm border border-calm/20" };
    }
    if (status === "paid") {
        return { key: status, label: "Paid", classes: "bg-brand/10 text-brand border border-brand/20" };
    }
    if (status === "printed") {
        return { key: status, label: "Printed", classes: "bg-warn/10 text-warn border border-warn/20" };
    }
    return { key: status, label: "Open", classes: "bg-stone-200/70 text-stone-700 border border-stone-300" };
}

function selectedInvoice() {
    return invoicesState.invoices.find((invoice) => invoice.id === invoicesState.selectedInvoiceId) || invoicesState.editor.invoice || null;
}

function setEditorPayload(data) {
    invoicesState.editor = {
        invoice: data.invoice || null,
        selected_time_entries: Array.isArray(data.selected_time_entries) ? data.selected_time_entries : [],
        selected_expenses: Array.isArray(data.selected_expenses) ? data.selected_expenses : [],
        eligible_time_entries: Array.isArray(data.eligible_time_entries) ? data.eligible_time_entries : [],
        eligible_expenses: Array.isArray(data.eligible_expenses) ? data.eligible_expenses : [],
        summary: data.summary || {}
    };
}

function currentSelectedTimeIds() {
    return new Set((invoicesState.editor.selected_time_entries || []).map((entry) => Number(entry.id)));
}

function currentSelectedExpenseIds() {
    return new Set((invoicesState.editor.selected_expenses || []).map((expense) => Number(expense.id)));
}

function recalculateEditorSummary() {
    const invoice = invoicesState.editor.invoice;
    if (!invoice) {
        return;
    }
    const timeTotal = (invoicesState.editor.selected_time_entries || []).reduce((sum, entry) => sum + (entry.line_total_cents || 0), 0);
    const expenseTotal = (invoicesState.editor.selected_expenses || []).reduce((sum, expense) => sum + (expense.line_total_cents || 0), 0);
    const invoiceTotal = timeTotal + expenseTotal;
    const priorBalance = invoice.prior_balance_cents || 0;
    const unappliedCredit = invoice.unapplied_credit_cents || 0;
    invoice.invoice_amount_cents = invoiceTotal;
    invoice.open_balance_cents = Math.max(0, invoiceTotal - (invoice.paid_amount_cents || 0));
    invoicesState.editor.summary = {
        ...(invoicesState.editor.summary || {}),
        time_total_cents: timeTotal,
        expense_total_cents: expenseTotal,
        invoice_total_cents: invoiceTotal,
        prior_balance_cents: priorBalance,
        unapplied_credit_cents: unappliedCredit,
        open_balance_after_issue_cents: Math.max(0, priorBalance + invoiceTotal - unappliedCredit)
    };
}

function upsertInvoice(invoice) {
    const index = invoicesState.invoices.findIndex((currentInvoice) => currentInvoice.id === invoice.id);
    if (index >= 0) {
        invoicesState.invoices.splice(index, 1, invoice);
    } else {
        invoicesState.invoices.unshift(invoice);
    }
}

async function requestJson(path, options = {}, fallbackMessage = "Request failed.") {
    const response = await fetch(invoicesUrl(path), {
        headers: {
            Accept: "application/json",
            ...(options.headers || {})
        },
        ...options
    });
    const payload = await response.json();
    if (!response.ok) {
        throw new Error(extractErrorMessage(payload, fallbackMessage));
    }
    return payload.data || {};
}

async function loadEditor(invoiceId) {
    if (!invoiceId) {
        invoicesState.editor = {
            invoice: null,
            selected_time_entries: [],
            selected_expenses: [],
            eligible_time_entries: [],
            eligible_expenses: [],
            summary: {}
        };
        render();
        return;
    }

    try {
        const data = await requestJson(`/${invoiceId}/editor`, {}, "Unable to load invoice details.");
        setEditorPayload(data);
        if (data.invoice) {
            invoicesState.selectedInvoiceId = data.invoice.id;
            upsertInvoice(data.invoice);
        }
        invoicesState.loadError = "";
    } catch (error) {
        invoicesState.loadError = extractErrorMessage(error, "Unable to load invoice details.");
    }
    render();
}

async function loadNewEditor(projectId, sourceInvoice = null) {
    const invoiceDate = sourceInvoice?.invoice_date || document.getElementById("invoice-date")?.value || TODAY;
    const termsDays = Number(sourceInvoice?.terms_days ?? 30);
    const query = new URLSearchParams({
        project_id: String(projectId),
        invoice_date: invoiceDate,
        terms_days: String(termsDays)
    });
    try {
        const data = await requestJson(`/new/editor?${query.toString()}`, {}, "Unable to load project invoice rows.");
        setEditorPayload(data);
        if (sourceInvoice && invoicesState.editor.invoice) {
            invoicesState.editor.invoice.id = sourceInvoice.id || null;
            invoicesState.editor.invoice.invoice_number = sourceInvoice.invoice_number || invoicesState.editor.invoice.invoice_number;
            invoicesState.editor.invoice.invoice_date = sourceInvoice.invoice_date || invoicesState.editor.invoice.invoice_date;
            invoicesState.editor.invoice.terms_days = sourceInvoice.terms_days ?? invoicesState.editor.invoice.terms_days;
            invoicesState.editor.invoice.po_number = sourceInvoice.po_number || null;
            invoicesState.editor.invoice.notes = sourceInvoice.notes || "";
            invoicesState.editor.invoice.issued_at = sourceInvoice.issued_at || null;
            invoicesState.editor.invoice.paid_amount_cents = sourceInvoice.paid_amount_cents || 0;
            invoicesState.editor.invoice.status = sourceInvoice.id ? sourceInvoice.status : "new";
        }
        invoicesState.selectedInvoiceId = sourceInvoice?.id || null;
        invoicesState.loadError = "";
    } catch (error) {
        invoicesState.loadError = extractErrorMessage(error, "Unable to load project invoice rows.");
    }
    render();
}

async function loadInvoices() {
    invoicesState.isLoading = true;
    invoicesState.loadError = "";
    render();

    try {
        const data = await requestJson("/bootstrap", {}, "Unable to load invoices.");
        invoicesState.projects = Array.isArray(data.projects) ? data.projects : [];
        invoicesState.invoices = Array.isArray(data.invoices) ? data.invoices : [];
        invoicesState.selectedInvoiceId = invoicesState.invoices[0]?.id || null;
        await loadEditor(invoicesState.selectedInvoiceId);
    } catch (error) {
        invoicesState.loadError = extractErrorMessage(error, "Unable to load invoices.");
        invoicesState.projects = [];
        invoicesState.invoices = [];
        invoicesState.selectedInvoiceId = null;
        invoicesState.editor.invoice = null;
    } finally {
        invoicesState.isLoading = false;
        render();
    }
}

function filteredInvoices() {
    const query = invoicesState.searchQuery.trim().toLowerCase();
    return invoicesState.invoices.filter((invoice) => {
        const status = deriveInvoiceStatus(invoice);
        const matchesStatus = invoicesState.statusFilter === "all" || status === invoicesState.statusFilter;
        const year = String(invoice.invoice_date).slice(0, 4);
        const matchesYear = invoicesState.yearFilter === "all" || year === invoicesState.yearFilter;
        const haystack = [invoice.invoice_number, invoice.customer_name, invoice.project_number, invoice.po_number || "", invoice.notes || ""].join(" ").toLowerCase();
        const matchesQuery = !query || haystack.includes(query);
        return matchesStatus && matchesYear && matchesQuery;
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
    const select = document.getElementById("invoice-project");
    if (!select) {
        return;
    }
    select.innerHTML = invoicesState.projects.map((project) => `<option value="${project.id}">${escapeHtml(project.project_number)} · ${escapeHtml(project.customer_name)}</option>`).join("");
}

function renderYearOptions() {
    const filter = document.getElementById("invoice-year-filter");
    if (!filter) {
        return;
    }
    const years = Array.from(new Set(invoicesState.invoices.map((invoice) => String(invoice.invoice_date).slice(0, 4)))).sort().reverse();
    filter.innerHTML = ['<option value="all">All Years</option>', ...years.map((year) => `<option value="${year}">${year}</option>`)].join("");
    filter.value = invoicesState.yearFilter;
}

function renderMetrics(invoices) {
    const openReceivables = invoices.reduce((sum, invoice) => sum + (deriveInvoiceStatus(invoice) !== "paid" ? (invoice.open_balance_cents || 0) : 0), 0);
    const printedAmount = invoices.reduce((sum, invoice) => sum + (deriveInvoiceStatus(invoice) === "printed" ? (invoice.open_balance_cents || 0) : 0), 0);
    const paidAmount = invoices.reduce((sum, invoice) => sum + (invoice.paid_amount_cents || 0), 0);
    const openAmount = invoices.reduce((sum, invoice) => sum + (deriveInvoiceStatus(invoice) === "draft" ? (invoice.invoice_amount_cents || 0) : 0), 0);
    setText("invoices-mode", invoicesState.isLoading ? "Loading" : "Served Mode");
    setText("metric-open-receivables", currency(openReceivables));
    setText("metric-pending-amount", currency(printedAmount));
    setText("metric-paid-amount", currency(paidAmount));
    setText("metric-draft-amount", currency(openAmount));
}

function renderStatusFilters() {
    document.querySelectorAll("[data-invoice-status-filter]").forEach((button) => {
        const isActive = button.dataset.invoiceStatusFilter === invoicesState.statusFilter;
        button.classList.toggle("bg-brand", isActive);
        button.classList.toggle("text-stone-50", isActive);
        button.classList.toggle("border-brand", isActive);
        button.classList.toggle("shadow-sm", isActive);
        button.classList.toggle("bg-panel/70", !isActive);
        button.classList.toggle("text-ink", !isActive);
        button.classList.toggle("border-line", !isActive);
    });
}

function renderInvoiceRows(invoices) {
    const tbody = document.getElementById("invoice-table-body");
    const emptyState = document.getElementById("invoice-empty-state");
    if (!tbody || !emptyState) {
        return;
    }
    if (invoicesState.isLoading) {
        tbody.innerHTML = "";
        setEmptyState("Loading invoices...");
        emptyState.classList.remove("hidden");
        return;
    }
    if (invoicesState.loadError) {
        tbody.innerHTML = "";
        setEmptyState(invoicesState.loadError);
        emptyState.classList.remove("hidden");
        return;
    }
    if (invoices.length === 0) {
        tbody.innerHTML = "";
        setEmptyState("No invoices match the current filter.");
        emptyState.classList.remove("hidden");
        return;
    }
    emptyState.classList.add("hidden");
    tbody.innerHTML = invoices.map((invoice) => {
        const status = invoiceStatusMeta(invoice);
        const isSelected = invoice.id === invoicesState.selectedInvoiceId;
        return `
            <tr class="cursor-pointer border-t border-line/70 ${isSelected ? "bg-brand/5" : "bg-white/30 hover:bg-white/60"}" data-invoice-select="${invoice.id}">
                <td class="px-4 py-4 align-top font-mono text-sm text-ink">${escapeHtml(invoice.invoice_number)}</td>
                <td class="px-4 py-4 align-top text-sm text-ink">${escapeHtml(invoice.customer_name)}</td>
                <td class="px-4 py-4 align-top text-sm text-ink">${escapeHtml(invoice.project_number)}</td>
                <td class="px-4 py-4 align-top text-sm text-ink">${escapeHtml(invoice.invoice_date)}</td>
                <td class="px-4 py-4 align-top text-right font-mono text-sm text-ink">${currency(invoice.invoice_amount_cents || 0)}</td>
                <td class="px-4 py-4 align-top"><span class="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${status.classes}">${escapeHtml(status.label)}</span></td>
            </tr>
        `;
    }).join("");
    tbody.querySelectorAll("[data-invoice-select]").forEach((row) => {
        row.addEventListener("click", async () => {
            invoicesState.selectedInvoiceId = Number(row.dataset.invoiceSelect);
            await loadEditor(invoicesState.selectedInvoiceId);
        });
    });
}

function renderSelectableSourceList(containerId, items, type, invoiceId, isDisabled, formatter) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }
    if (items.length === 0) {
        container.innerHTML = '<p class="rounded-xl border border-dashed border-line bg-panel/35 px-3 py-3 text-sm text-muted">No eligible rows for this invoice.</p>';
        return;
    }
    container.innerHTML = items.map((item) => formatter(item, type, invoiceId, isDisabled)).join("");
    container.querySelectorAll("[data-selection-type]").forEach((input) => {
        input.addEventListener("change", () => {
            toggleSelection(input.dataset.selectionType, Number(input.dataset.selectionId), input.checked);
        });
    });
}

function updateEditorSummary(invoice, summary) {
    const status = invoiceStatusMeta(invoice);
    const chip = document.getElementById("invoice-editor-status-chip");
    if (chip) {
        chip.className = `rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${status.classes}`;
        chip.textContent = status.label;
    }
    setText("invoice-editor-title", invoice.id ? `${invoice.invoice_number} · ${invoice.project_number}` : "New Invoice");
    setText("invoice-detail-customer", invoice.customer_name);
    setText("invoice-detail-total", currency(summary.invoice_total_cents));
    setText("invoice-detail-open-balance", currency(invoice.open_balance_cents || 0));
    setText("invoice-summary-time", currency(summary.time_total_cents));
    setText("invoice-summary-expense", currency(summary.expense_total_cents));
    setText("invoice-summary-total", currency(summary.invoice_total_cents));
    setText("invoice-summary-prior-balance", currency(summary.prior_balance_cents));
    setText("invoice-summary-credit", currency(summary.unapplied_credit_cents));
    setText("invoice-summary-open-after-issue", currency(summary.open_balance_after_issue_cents));
}

function renderEditor(invoice) {
    if (!invoice) {
        return;
    }
    const projectSelect = document.getElementById("invoice-project");
    if (!projectSelect) {
        return;
    }
    document.getElementById("invoice-number").value = invoice.invoice_number;
    projectSelect.value = String(invoice.project_id);
    document.getElementById("invoice-date").value = invoice.invoice_date;
    document.getElementById("invoice-po-number").value = invoice.po_number || "";
    document.getElementById("invoice-notes").value = invoice.notes || "";

    ["invoice-number", "invoice-project", "invoice-date", "invoice-po-number", "invoice-notes"].forEach((id) => {
        document.getElementById(id).disabled = invoicesState.isSaving;
    });

    const summary = invoicesState.editor.summary || {};
    updateEditorSummary(invoice, summary);

    const selectedTimeIds = currentSelectedTimeIds();
    const selectedExpenseIds = currentSelectedExpenseIds();
    const eligibleTime = invoicesState.editor.eligible_time_entries || [];
    const eligibleExpenseRows = invoicesState.editor.eligible_expenses || [];

    setText("eligible-time-count", `${eligibleTime.length} rows`);
    setText("eligible-expense-count", `${eligibleExpenseRows.length} rows`);

    renderSelectableSourceList(
        "eligible-time-list",
        eligibleTime,
        "time",
        selectedTimeIds,
        invoicesState.isSaving,
        (entry, type, selectedIds, disabled) => `
            <label class="flex items-start gap-3 rounded-xl border border-line bg-panel/35 px-3 py-3 ${disabled ? "opacity-70" : "cursor-pointer hover:bg-white/80"}">
                <input class="mt-1 rounded border-line text-brand focus:ring-brand/30" data-selection-id="${entry.id}" data-selection-type="${type}" ${selectedIds.has(Number(entry.id)) ? "checked" : ""} ${disabled ? "disabled" : ""} type="checkbox">
                <div class="min-w-0 flex-1">
                    <p class="font-mono text-xs text-ink">${escapeHtml(entry.entry_date)} · ${timeHours(entry.minutes)}h · ${escapeHtml(entry.rate_code)}</p>
                    <p class="mt-1 text-sm text-ink">${escapeHtml(entry.description)}</p>
                    <p class="mt-1 font-mono text-xs text-muted">${currency(entry.line_total_cents)}</p>
                </div>
            </label>`
    );
    renderSelectableSourceList(
        "eligible-expenses-list",
        eligibleExpenseRows,
        "expense",
        selectedExpenseIds,
        invoicesState.isSaving,
        (expense, type, selectedIds, disabled) => `
            <label class="flex items-start gap-3 rounded-xl border border-line bg-panel/35 px-3 py-3 ${disabled ? "opacity-70" : "cursor-pointer hover:bg-white/80"}">
                <input class="mt-1 rounded border-line text-brand focus:ring-brand/30" data-selection-id="${expense.id}" data-selection-type="${type}" ${selectedIds.has(Number(expense.id)) ? "checked" : ""} ${disabled ? "disabled" : ""} type="checkbox">
                <div class="min-w-0 flex-1">
                    <p class="font-mono text-xs text-ink">${escapeHtml(expense.entry_date)} · ${escapeHtml(expense.category)}</p>
                    <p class="mt-1 text-sm text-ink">${escapeHtml(expense.vendor)} · ${escapeHtml(expense.description)}</p>
                    <p class="mt-1 font-mono text-xs text-muted">${currency(expense.line_total_cents)}</p>
                </div>
            </label>`
    );

    const saveButton = document.getElementById("save-invoice-button");
    if (saveButton) {
        saveButton.disabled = invoicesState.isSaving;
        saveButton.classList.toggle("opacity-60", invoicesState.isSaving);
        saveButton.textContent = invoicesState.isSaving ? "Saving..." : "Save/Print Invoice";
    }
    const deleteButton = document.getElementById("delete-invoice-button");
    if (deleteButton) {
        const cannotDelete = Boolean(invoice.id) || invoicesState.isSaving;
        deleteButton.disabled = cannotDelete;
        deleteButton.classList.toggle("opacity-60", cannotDelete);
        deleteButton.textContent = invoice.id ? "Saved Invoice" : "Discard New";
    }
}

function invoicePayloadFromForm(currentInvoice) {
    const invoiceDate = String(document.getElementById("invoice-date")?.value || currentInvoice?.invoice_date || TODAY);
    return {
        invoice_number: String(document.getElementById("invoice-number")?.value || currentInvoice?.invoice_number || "").trim() || null,
        project_id: Number(document.getElementById("invoice-project")?.value || currentInvoice?.project_id || 0),
        invoice_date: invoiceDate,
        terms_days: Number(currentInvoice?.terms_days ?? 30),
        po_number: String(document.getElementById("invoice-po-number")?.value || "").trim() || null,
        notes: String(document.getElementById("invoice-notes")?.value || "")
    };
}

function syncSelectedInvoiceFromForm() {
    const invoice = selectedInvoice();
    if (!invoice) {
        return;
    }
    const payload = invoicePayloadFromForm(invoice);
    const project = projectById(payload.project_id);
    invoice.invoice_number = payload.invoice_number || invoice.invoice_number;
    invoice.project_id = payload.project_id;
    invoice.project_number = project?.project_number || invoice.project_number;
    invoice.customer_id = project?.customer_id || invoice.customer_id;
    invoice.customer_name = project?.customer_name || invoice.customer_name;
    invoice.invoice_date = payload.invoice_date;
    invoice.terms_days = payload.terms_days;
    invoice.po_number = payload.po_number;
    invoice.notes = payload.notes;
}

function toggleSelection(type, itemId, checked) {
    const invoice = selectedInvoice();
    if (!invoice || invoicesState.isSaving) {
        return;
    }
    const timeEntryIds = currentSelectedTimeIds();
    const expenseIds = currentSelectedExpenseIds();
    if (type === "time") {
        if (checked) {
            timeEntryIds.add(itemId);
        } else {
            timeEntryIds.delete(itemId);
        }
    } else if (checked) {
        expenseIds.add(itemId);
    } else {
        expenseIds.delete(itemId);
    }

    invoicesState.editor.selected_time_entries = (invoicesState.editor.eligible_time_entries || []).filter((entry) => timeEntryIds.has(Number(entry.id)));
    invoicesState.editor.selected_expenses = (invoicesState.editor.eligible_expenses || []).filter((expense) => expenseIds.has(Number(expense.id)));
    recalculateEditorSummary();
    render();
}

async function createDraftInvoice(sourceInvoice = null) {
    if (invoicesState.isSaving || invoicesState.projects.length === 0) {
        return;
    }
    await loadNewEditor(sourceInvoice?.project_id || invoicesState.projects[0].id, sourceInvoice);
    invoicesState.loadError = "";
    render();
}

async function savePrintInvoice() {
    const invoice = selectedInvoice();
    if (!invoice || invoicesState.isSaving) {
        return;
    }

    const printWindow = window.open("about:blank", "_blank");
    if (!printWindow) {
        invoicesState.loadError = "Allow pop-ups to save and print the invoice.";
        render();
        return;
    }

    invoicesState.isSaving = true;
    render();
    try {
        const data = await requestJson(
            "/save-print",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    invoice: {
                        id: invoice.id || null,
                        ...invoicePayloadFromForm(invoice)
                    },
                    time_entry_ids: Array.from(currentSelectedTimeIds()),
                    expense_ids: Array.from(currentSelectedExpenseIds())
                })
            },
            "Unable to save and print invoice."
        );
        if (data.invoice) {
            upsertInvoice(data.invoice);
            invoicesState.selectedInvoiceId = data.invoice.id;
        }
        if (data.editor) {
            setEditorPayload(data.editor);
        } else if (data.invoice) {
            await loadEditor(data.invoice.id);
        }
        if (data.printable_url) {
            printWindow.location.replace(`${data.printable_url}?autoprint=1`);
        } else {
            printWindow.close();
        }
        invoicesState.loadError = "";
    } catch (error) {
        printWindow.close();
        invoicesState.loadError = extractErrorMessage(error, "Unable to save and print invoice.");
    } finally {
        invoicesState.isSaving = false;
        render();
    }
}

async function deleteDraftInvoice() {
    const invoice = selectedInvoice();
    if (!invoice || invoice.id || invoicesState.isSaving) {
        return;
    }

    invoicesState.editor = {
        invoice: null,
        selected_time_entries: [],
        selected_expenses: [],
        eligible_time_entries: [],
        eligible_expenses: [],
        summary: {}
    };
    invoicesState.selectedInvoiceId = invoicesState.invoices[0]?.id || null;
    if (invoicesState.selectedInvoiceId) {
        await loadEditor(invoicesState.selectedInvoiceId);
        return;
    }
    render();
}

function bindEvents() {
    document.getElementById("invoice-search")?.addEventListener("input", (event) => {
        invoicesState.searchQuery = event.target.value;
        render();
    });
    document.getElementById("invoice-year-filter")?.addEventListener("change", (event) => {
        invoicesState.yearFilter = event.target.value;
        render();
    });
    document.querySelectorAll("[data-invoice-status-filter]").forEach((button) => {
        button.addEventListener("click", () => {
            invoicesState.statusFilter = button.dataset.invoiceStatusFilter || "all";
            render();
        });
    });
    document.getElementById("new-invoice-button")?.addEventListener("click", () => {
        void createDraftInvoice(null);
    });
    document.getElementById("delete-invoice-button")?.addEventListener("click", () => {
        void deleteDraftInvoice();
    });
    document.getElementById("save-invoice-button")?.addEventListener("click", () => {
        void savePrintInvoice();
    });
    document.getElementById("reset-invoice-filters-button")?.addEventListener("click", () => {
        invoicesState.searchQuery = "";
        invoicesState.yearFilter = "all";
        invoicesState.statusFilter = "all";
        const search = document.getElementById("invoice-search");
        if (search) {
            search.value = "";
        }
        render();
    });
    document.getElementById("invoice-number")?.addEventListener("input", () => {
        syncSelectedInvoiceFromForm();
        render();
    });
    document.getElementById("invoice-project")?.addEventListener("change", (event) => {
        const currentInvoice = selectedInvoice();
        const payload = invoicePayloadFromForm(currentInvoice);
        const sourceInvoice = {
            ...(currentInvoice || {}),
            ...payload,
            project_id: Number(event.target.value || payload.project_id || 0)
        };
        void loadNewEditor(sourceInvoice.project_id, sourceInvoice);
    });
    document.getElementById("invoice-date")?.addEventListener("input", () => {
        syncSelectedInvoiceFromForm();
        render();
    });
    document.getElementById("invoice-po-number")?.addEventListener("input", () => {
        syncSelectedInvoiceFromForm();
        render();
    });
    document.getElementById("invoice-notes")?.addEventListener("input", () => {
        syncSelectedInvoiceFromForm();
        render();
    });
}

function render() {
    renderNavState();
    renderProjectOptions();
    renderYearOptions();
    renderStatusFilters();
    const invoices = filteredInvoices();
    renderMetrics(invoices);
    renderInvoiceRows(invoices);
    renderEditor(invoicesState.editor.invoice || selectedInvoice());
}

window.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    render();
    loadInvoices();
});
