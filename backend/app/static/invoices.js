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
        detail.textContent = invoicesState.loadError ? "Retry after the API is available or correct the reported validation issue." : "Adjust the year or status filter, or create a new invoice draft.";
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

function dueDateFromTerms(invoiceDate, termsDays) {
    const parts = String(invoiceDate).split("-").map((value) => Number(value));
    if (parts.length !== 3 || parts.some((value) => !Number.isFinite(value))) {
        return invoiceDate;
    }
    const nextDate = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
    nextDate.setUTCDate(nextDate.getUTCDate() + Number(termsDays || 0));
    return nextDate.toISOString().slice(0, 10);
}

function termsDaysFromDates(invoiceDate, dueDate) {
    const invoiceAt = Date.parse(`${invoiceDate}T00:00:00Z`);
    const dueAt = Date.parse(`${dueDate}T00:00:00Z`);
    if (!Number.isFinite(invoiceAt) || !Number.isFinite(dueAt)) {
        return 0;
    }
    return Math.max(0, Math.round((dueAt - invoiceAt) / 86400000));
}

function timeHours(minutes) {
    return ((minutes || 0) / 60).toFixed(2);
}

function deriveInvoiceStatus(invoice) {
    return invoice?.status || "draft";
}

function invoiceStatusMeta(invoice) {
    const status = deriveInvoiceStatus(invoice);
    if (status === "paid") {
        return { key: status, label: "Paid", classes: "bg-brand/10 text-brand border border-brand/20" };
    }
    if (status === "overdue") {
        return { key: status, label: "Overdue", classes: "bg-danger/10 text-danger border border-danger/20" };
    }
    if (status === "pending") {
        return { key: status, label: "Pending", classes: "bg-warn/10 text-warn border border-warn/20" };
    }
    return { key: status, label: "Draft", classes: "bg-stone-200/70 text-stone-700 border border-stone-300" };
}

function selectedInvoice() {
    return invoicesState.invoices.find((invoice) => invoice.id === invoicesState.selectedInvoiceId) || invoicesState.editor.invoice || null;
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
        invoicesState.editor = {
            invoice: data.invoice || null,
            selected_time_entries: Array.isArray(data.selected_time_entries) ? data.selected_time_entries : [],
            selected_expenses: Array.isArray(data.selected_expenses) ? data.selected_expenses : [],
            eligible_time_entries: Array.isArray(data.eligible_time_entries) ? data.eligible_time_entries : [],
            eligible_expenses: Array.isArray(data.eligible_expenses) ? data.eligible_expenses : [],
            summary: data.summary || {}
        };
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
    select.innerHTML = invoicesState.projects.map((project) => `<option value="${project.id}">${project.project_number} · ${project.customer_name}</option>`).join("");
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
    const overdueAmount = invoices.reduce((sum, invoice) => sum + (deriveInvoiceStatus(invoice) === "overdue" ? (invoice.open_balance_cents || 0) : 0), 0);
    const paidAmount = invoices.reduce((sum, invoice) => sum + (invoice.paid_amount_cents || 0), 0);
    const draftAmount = invoices.reduce((sum, invoice) => sum + (deriveInvoiceStatus(invoice) === "draft" ? (invoice.invoice_amount_cents || 0) : 0), 0);
    setText("invoices-mode", invoicesState.isLoading ? "Loading" : "Served Mode");
    setText("metric-open-receivables", currency(openReceivables));
    setText("metric-overdue-amount", currency(overdueAmount));
    setText("metric-paid-amount", currency(paidAmount));
    setText("metric-draft-amount", currency(draftAmount));
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
                <td class="px-4 py-4 align-top font-mono text-sm text-ink">${invoice.invoice_number}</td>
                <td class="px-4 py-4 align-top text-sm text-ink">${invoice.customer_name}</td>
                <td class="px-4 py-4 align-top text-sm text-ink">${invoice.project_number}</td>
                <td class="px-4 py-4 align-top text-sm text-ink">${invoice.due_date}</td>
                <td class="px-4 py-4 align-top text-right font-mono text-sm text-ink">${currency(invoice.invoice_amount_cents || 0)}</td>
                <td class="px-4 py-4 align-top"><span class="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${status.classes}">${status.label}</span></td>
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

function renderSourceList(containerId, items, emptyLabel, formatter) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }
    if (items.length === 0) {
        container.innerHTML = `<p class="rounded-xl border border-dashed border-line bg-panel/35 px-3 py-3 text-sm text-muted">${emptyLabel}</p>`;
        return;
    }
    container.innerHTML = items.map(formatter).join("");
}

function renderSelectableSourceList(containerId, items, type, invoiceId, isLocked, formatter) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }
    if (items.length === 0) {
        container.innerHTML = '<p class="rounded-xl border border-dashed border-line bg-panel/35 px-3 py-3 text-sm text-muted">No eligible rows for this invoice.</p>';
        return;
    }
    container.innerHTML = items.map((item) => formatter(item, type, invoiceId, isLocked)).join("");
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
    setText("invoice-editor-title", `${invoice.invoice_number} · ${invoice.project_number}`);
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
    const isLocked = Boolean(invoice.issued_at);
    document.getElementById("invoice-number").value = invoice.invoice_number;
    projectSelect.value = String(invoice.project_id);
    document.getElementById("invoice-date").value = invoice.invoice_date;
    document.getElementById("invoice-due-date").value = invoice.due_date;
    document.getElementById("invoice-po-number").value = invoice.po_number || "";
    document.getElementById("invoice-notes").value = invoice.notes || "";

    ["invoice-number", "invoice-project", "invoice-date", "invoice-due-date", "invoice-po-number", "invoice-notes"].forEach((id) => {
        document.getElementById(id).disabled = isLocked || invoicesState.isSaving;
    });

    const summary = invoicesState.editor.summary || {};
    updateEditorSummary(invoice, summary);

    const selectedTime = invoicesState.editor.selected_time_entries || [];
    const selectedExpenseRows = invoicesState.editor.selected_expenses || [];
    const eligibleTime = invoicesState.editor.eligible_time_entries || [];
    const eligibleExpenseRows = invoicesState.editor.eligible_expenses || [];

    renderSourceList(
        "selected-time-list",
        selectedTime,
        "No time entries selected.",
        (entry) => `<div class="rounded-xl border border-line bg-panel/40 px-3 py-3"><p class="font-mono text-xs text-ink">${entry.entry_date} · ${timeHours(entry.minutes)}h · ${entry.rate_code}</p><p class="mt-1 text-sm text-ink">${entry.description}</p><p class="mt-1 font-mono text-xs text-muted">${currency(entry.line_total_cents)}</p></div>`
    );
    renderSourceList(
        "selected-expenses-list",
        selectedExpenseRows,
        "No expenses selected.",
        (expense) => `<div class="rounded-xl border border-line bg-panel/40 px-3 py-3"><p class="font-mono text-xs text-ink">${expense.entry_date} · ${expense.category}</p><p class="mt-1 text-sm text-ink">${expense.vendor} · ${expense.description}</p><p class="mt-1 font-mono text-xs text-muted">${currency(expense.line_total_cents)}</p></div>`
    );

    setText("eligible-time-count", `${eligibleTime.length} rows`);
    setText("eligible-expense-count", `${eligibleExpenseRows.length} rows`);

    renderSelectableSourceList(
        "eligible-time-list",
        eligibleTime,
        "time",
        invoice.id,
        isLocked,
        (entry, type, invoiceId, locked) => `
            <label class="flex items-start gap-3 rounded-xl border border-line bg-panel/35 px-3 py-3 ${locked ? "opacity-70" : "cursor-pointer hover:bg-white/80"}">
                <input class="mt-1 rounded border-line text-brand focus:ring-brand/30" data-selection-id="${entry.id}" data-selection-type="${type}" ${entry.invoice_id === invoiceId ? "checked" : ""} ${locked ? "disabled" : ""} type="checkbox">
                <div class="min-w-0 flex-1">
                    <p class="font-mono text-xs text-ink">${entry.entry_date} · ${timeHours(entry.minutes)}h · ${entry.rate_code}</p>
                    <p class="mt-1 text-sm text-ink">${entry.description}</p>
                    <p class="mt-1 font-mono text-xs text-muted">${currency(entry.line_total_cents)}</p>
                </div>
            </label>`
    );
    renderSelectableSourceList(
        "eligible-expenses-list",
        eligibleExpenseRows,
        "expense",
        invoice.id,
        isLocked,
        (expense, type, invoiceId, locked) => `
            <label class="flex items-start gap-3 rounded-xl border border-line bg-panel/35 px-3 py-3 ${locked ? "opacity-70" : "cursor-pointer hover:bg-white/80"}">
                <input class="mt-1 rounded border-line text-brand focus:ring-brand/30" data-selection-id="${expense.id}" data-selection-type="${type}" ${expense.invoice_id === invoiceId ? "checked" : ""} ${locked ? "disabled" : ""} type="checkbox">
                <div class="min-w-0 flex-1">
                    <p class="font-mono text-xs text-ink">${expense.entry_date} · ${expense.category}</p>
                    <p class="mt-1 text-sm text-ink">${expense.vendor} · ${expense.description}</p>
                    <p class="mt-1 font-mono text-xs text-muted">${currency(expense.line_total_cents)}</p>
                </div>
            </label>`
    );

    const issueButton = document.getElementById("issue-invoice-button");
    if (issueButton) {
        issueButton.disabled = isLocked || invoicesState.isSaving;
        issueButton.classList.toggle("opacity-60", isLocked);
        issueButton.textContent = isLocked ? "Already Issued" : "Issue Invoice";
    }
    const saveButton = document.getElementById("save-invoice-button");
    if (saveButton) {
        saveButton.disabled = isLocked || invoicesState.isSaving;
        saveButton.classList.toggle("opacity-60", isLocked || invoicesState.isSaving);
        saveButton.textContent = invoicesState.isSaving ? "Saving..." : "Save Invoice";
    }
    const pdfButton = document.getElementById("view-invoice-pdf-button");
    if (pdfButton) {
        const canViewPdf = Boolean(invoice.issued_at);
        pdfButton.href = canViewPdf ? `/api/invoices/${invoice.id}/pdf` : "#";
        pdfButton.classList.toggle("opacity-60", !canViewPdf);
        pdfButton.classList.toggle("pointer-events-none", !canViewPdf);
        pdfButton.textContent = canViewPdf ? "View PDF" : "PDF Unavailable";
    }
}

function invoicePayloadFromForm(currentInvoice) {
    const invoiceDate = String(document.getElementById("invoice-date")?.value || currentInvoice?.invoice_date || TODAY);
    const dueDate = String(document.getElementById("invoice-due-date")?.value || currentInvoice?.due_date || dueDateFromTerms(invoiceDate, 30));
    return {
        invoice_number: String(document.getElementById("invoice-number")?.value || currentInvoice?.invoice_number || "").trim() || null,
        project_id: Number(document.getElementById("invoice-project")?.value || currentInvoice?.project_id || 0),
        invoice_date: invoiceDate,
        terms_days: termsDaysFromDates(invoiceDate, dueDate),
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
    invoice.due_date = dueDateFromTerms(payload.invoice_date, payload.terms_days);
    invoice.po_number = payload.po_number;
    invoice.notes = payload.notes;
}

async function toggleSelection(type, itemId, checked) {
    const invoice = selectedInvoice();
    if (!invoice || invoice.issued_at || invoicesState.isSaving) {
        return;
    }
    const timeEntryIds = new Set((invoicesState.editor.selected_time_entries || []).map((entry) => entry.id));
    const expenseIds = new Set((invoicesState.editor.selected_expenses || []).map((expense) => expense.id));
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

    invoicesState.isSaving = true;
    render();
    try {
        const data = await requestJson(
            `/${invoice.id}/selection`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    time_entry_ids: Array.from(timeEntryIds),
                    expense_ids: Array.from(expenseIds)
                })
            },
            "Unable to update invoice selection."
        );
        invoicesState.editor = data;
        if (data.invoice) {
            upsertInvoice(data.invoice);
        }
        invoicesState.loadError = "";
    } catch (error) {
        invoicesState.loadError = extractErrorMessage(error, "Unable to update invoice selection.");
    } finally {
        invoicesState.isSaving = false;
        render();
    }
}

async function createDraftInvoice(sourceInvoice = null) {
    const sourceProject = sourceInvoice ? projectById(sourceInvoice.project_id) : invoicesState.projects[0];
    if (!sourceProject || invoicesState.isSaving) {
        return;
    }
    const payload = {
        project_id: sourceProject.id,
        invoice_date: TODAY,
        terms_days: sourceInvoice?.terms_days ?? 30,
        po_number: sourceInvoice?.po_number || null,
        notes: sourceInvoice?.notes || "Thank you for your business."
    };

    invoicesState.isSaving = true;
    render();
    try {
        const data = await requestJson(
            "",
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            },
            "Unable to create invoice draft."
        );
        if (data.invoice) {
            upsertInvoice(data.invoice);
            invoicesState.selectedInvoiceId = data.invoice.id;
            await loadEditor(data.invoice.id);
        }
        invoicesState.loadError = "";
    } catch (error) {
        invoicesState.loadError = extractErrorMessage(error, "Unable to create invoice draft.");
    } finally {
        invoicesState.isSaving = false;
        render();
    }
}

async function saveDraftInvoice() {
    const invoice = selectedInvoice();
    if (!invoice || invoice.issued_at || invoicesState.isSaving) {
        return;
    }

    invoicesState.isSaving = true;
    render();
    try {
        const data = await requestJson(
            `/${invoice.id}`,
            {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(invoicePayloadFromForm(invoice))
            },
            "Unable to save invoice."
        );
        if (data.invoice) {
            upsertInvoice(data.invoice);
            await loadEditor(data.invoice.id);
        }
        invoicesState.loadError = "";
    } catch (error) {
        invoicesState.loadError = extractErrorMessage(error, "Unable to save invoice.");
    } finally {
        invoicesState.isSaving = false;
        render();
    }
}

async function issueInvoice() {
    const invoice = selectedInvoice();
    if (!invoice || invoice.issued_at || invoicesState.isSaving) {
        return;
    }

    await saveDraftInvoice();
    if (invoicesState.loadError) {
        return;
    }

    invoicesState.isSaving = true;
    render();
    try {
        const data = await requestJson(
            `/${invoice.id}/issue`,
            {
                method: "POST"
            },
            "Unable to issue invoice."
        );
        invoicesState.editor = {
            invoice: data.invoice || null,
            selected_time_entries: Array.isArray(data.selected_time_entries) ? data.selected_time_entries : [],
            selected_expenses: Array.isArray(data.selected_expenses) ? data.selected_expenses : [],
            eligible_time_entries: Array.isArray(data.eligible_time_entries) ? data.eligible_time_entries : [],
            eligible_expenses: Array.isArray(data.eligible_expenses) ? data.eligible_expenses : [],
            summary: data.summary || {}
        };
        if (data.invoice) {
            upsertInvoice(data.invoice);
        }
        invoicesState.loadError = "";
    } catch (error) {
        invoicesState.loadError = extractErrorMessage(error, "Unable to issue invoice.");
    } finally {
        invoicesState.isSaving = false;
        render();
    }
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
    document.getElementById("duplicate-invoice-button")?.addEventListener("click", () => {
        void createDraftInvoice(selectedInvoice());
    });
    document.getElementById("save-invoice-button")?.addEventListener("click", saveDraftInvoice);
    document.getElementById("issue-invoice-button")?.addEventListener("click", issueInvoice);
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
    document.getElementById("invoice-project")?.addEventListener("change", () => {
        syncSelectedInvoiceFromForm();
        render();
    });
    document.getElementById("invoice-date")?.addEventListener("input", () => {
        syncSelectedInvoiceFromForm();
        render();
    });
    document.getElementById("invoice-due-date")?.addEventListener("input", () => {
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