const TODAY = "2026-05-31";

const paymentsState = {
    customers: [],
    payments: [],
    editor: {
        payment: null,
        applications: [],
        open_invoices: []
    },
    applicationDrafts: {},
    searchQuery: "",
    statusFilter: "all",
    customerFilter: "all",
    yearFilter: "all",
    selectedPaymentId: null,
    isLoading: true,
    isSaving: false,
    loadError: ""
};

function paymentsUrl(path = "") {
    return `/api/payments${path}`;
}

function setEmptyState(message) {
    const element = document.getElementById("payment-empty-state");
    if (!element) {
        return;
    }
    const heading = element.querySelector("p.font-display");
    const detail = element.querySelector("p.mt-2");
    if (heading) {
        heading.textContent = message;
    }
    if (detail) {
        detail.textContent = paymentsState.loadError
            ? "Retry after the API is available."
            : "Adjust the customer, year, or status filter, or create a new payment draft.";
    }
}

async function requestJson(path, options = {}, fallbackMessage = "Request failed.") {
    return apiRequestJson(paymentsUrl(), path, options, fallbackMessage);
}

function customerById(customerId) {
    return paymentsState.customers.find((customer) => customer.id === Number(customerId)) || null;
}

function selectedPayment() {
    return paymentsState.editor.payment || paymentsState.payments.find((payment) => payment.id === paymentsState.selectedPaymentId) || null;
}

function createUnsavedPayment(customer, sourcePayment = null) {
    return {
        id: null,
        customer_id: customer.id,
        customer_name: customer.customer_name,
        payment_date: TODAY,
        reference_number: sourcePayment ? `${sourcePayment.reference_number}-COPY` : "",
        amount_cents: sourcePayment?.amount_cents || 0,
        applied_amount_cents: 0,
        unapplied_amount_cents: sourcePayment?.amount_cents || 0,
        application_status: "unapplied",
        notes: sourcePayment?.notes || "",
        updated_at: ""
    };
}

function paymentStatus(appliedAmountCents, amountCents) {
    if (appliedAmountCents <= 0) {
        return "unapplied";
    }
    if (appliedAmountCents >= amountCents) {
        return "fully_applied";
    }
    return "partially_applied";
}

function paymentPreview(payment) {
    const openInvoices = paymentsState.editor.open_invoices || [];
    const draftAppliedAmount = openInvoices.reduce((sum, invoice) => {
        const value = paymentsState.applicationDrafts[invoice.id];
        return sum + (Number.isFinite(value) ? value : (invoice.current_applied_cents || 0));
    }, 0);
    const appliedAmount = payment && paymentsState.editor.payment && payment.id === paymentsState.editor.payment.id
        ? draftAppliedAmount
        : (payment?.applied_amount_cents || 0);
    const amountCents = payment?.amount_cents || 0;
    return {
        applied_amount_cents: appliedAmount,
        unapplied_amount_cents: Math.max(0, amountCents - appliedAmount),
        application_status: paymentStatus(appliedAmount, amountCents)
    };
}

function paymentStatusMetaFromStatus(status) {
    if (status === "fully_applied") {
        return { label: "Fully Applied", classes: "bg-brand/10 text-brand border border-brand/20" };
    }
    if (status === "partially_applied") {
        return { label: "Partially Applied", classes: "bg-warn/10 text-warn border border-warn/20" };
    }
    return { label: "Unapplied", classes: "bg-stone-200/70 text-stone-700 border border-stone-300" };
}

function paymentStatusMeta(payment) {
    return paymentStatusMetaFromStatus(payment.application_status);
}

function updatePaymentSummary(payment) {
    const preview = paymentPreview(payment);
    const status = paymentStatusMetaFromStatus(preview.application_status);
    const chip = document.getElementById("payment-editor-status-chip");
    if (chip) {
        chip.className = `rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${status.classes}`;
        chip.textContent = status.label;
    }

    setText("payment-detail-unapplied", currency(preview.unapplied_amount_cents));
    setText("payment-summary-applied", currency(preview.applied_amount_cents));
    setText("payment-summary-unapplied", currency(preview.unapplied_amount_cents));
    setText("payment-summary-status", status.label);
}

function updatePaymentHeader(payment) {
    if (!payment) {
        return;
    }
    setText("payment-editor-title", `${payment.reference_number} - ${payment.payment_date}`);
    setText("payment-detail-customer", payment.customer_name);
    setText("payment-detail-amount", currency(payment.amount_cents));
    updatePaymentSummary(payment);
}

function invoiceStatusMeta(invoice) {
    if (invoice.status === "paid") {
        return { label: "Paid", classes: "bg-brand/10 text-brand border border-brand/20" };
    }
    return { label: "Pending", classes: "bg-calm/10 text-calm border border-calm/20" };
}

function upsertPayment(payment) {
    const index = paymentsState.payments.findIndex((currentPayment) => currentPayment.id === payment.id);
    if (index >= 0) {
        paymentsState.payments.splice(index, 1, payment);
    } else {
        paymentsState.payments.unshift(payment);
    }
}

function setEditorPayload(data) {
    paymentsState.editor = {
        payment: data.payment || null,
        applications: Array.isArray(data.applications) ? data.applications : [],
        open_invoices: Array.isArray(data.open_invoices) ? data.open_invoices : []
    };
    paymentsState.applicationDrafts = Object.fromEntries(
        paymentsState.editor.open_invoices.map((invoice) => [invoice.id, invoice.current_applied_cents || 0])
    );
    if (data.payment) {
        paymentsState.selectedPaymentId = data.payment.id;
        upsertPayment(data.payment);
    }
}

async function loadEditor(paymentId) {
    if (!paymentId) {
        paymentsState.editor = { payment: null, applications: [], open_invoices: [] };
        paymentsState.applicationDrafts = {};
        render();
        return;
    }

    try {
        const data = await requestJson(`/${paymentId}/editor`, {}, "Unable to load payment details.");
        setEditorPayload(data);
        paymentsState.loadError = "";
    } catch (error) {
        window.alert(extractErrorMessage(error, "Unable to load payment details."));
    }
    render();
}

async function loadCustomerOpenInvoices(customerId) {
    if (!customerId) {
        paymentsState.editor.applications = [];
        paymentsState.editor.open_invoices = [];
        paymentsState.applicationDrafts = {};
        render();
        return;
    }

    try {
        const data = await requestJson(`/customers/${customerId}/open-invoices`, {}, "Unable to load open invoices.");
        paymentsState.editor.applications = [];
        paymentsState.editor.open_invoices = Array.isArray(data.open_invoices) ? data.open_invoices : [];
        paymentsState.applicationDrafts = Object.fromEntries(
            paymentsState.editor.open_invoices.map((invoice) => [invoice.id, invoice.current_applied_cents || 0])
        );
        paymentsState.loadError = "";
    } catch (error) {
        window.alert(extractErrorMessage(error, "Unable to load open invoices."));
        paymentsState.editor.applications = [];
        paymentsState.editor.open_invoices = [];
        paymentsState.applicationDrafts = {};
    }
    render();
}

async function loadPayments() {
    paymentsState.isLoading = true;
    paymentsState.loadError = "";
    render();

    try {
        const data = await requestJson("/bootstrap", {}, "Unable to load payments.");
        paymentsState.customers = Array.isArray(data.customers) ? data.customers : [];
        paymentsState.payments = Array.isArray(data.payments) ? data.payments : [];
        paymentsState.selectedPaymentId = paymentsState.payments[0]?.id || null;
        await loadEditor(paymentsState.selectedPaymentId);
    } catch (error) {
        paymentsState.loadError = extractErrorMessage(error, "Unable to load payments.");
        paymentsState.customers = [];
        paymentsState.payments = [];
        paymentsState.selectedPaymentId = null;
        paymentsState.editor = { payment: null, applications: [], open_invoices: [] };
        paymentsState.applicationDrafts = {};
    } finally {
        paymentsState.isLoading = false;
        render();
    }
}

function filteredPayments() {
    const query = paymentsState.searchQuery.trim().toLowerCase();
    return paymentsState.payments.filter((payment) => {
        const matchesStatus = paymentsState.statusFilter === "all" || payment.application_status === paymentsState.statusFilter;
        const matchesCustomer = paymentsState.customerFilter === "all" || String(payment.customer_id) === paymentsState.customerFilter;
        const paymentYear = String(payment.payment_date).slice(0, 4);
        const matchesYear = paymentsState.yearFilter === "all" || paymentYear === paymentsState.yearFilter;
        const haystack = [payment.customer_name, payment.reference_number, payment.notes || ""].join(" ").toLowerCase();
        const matchesQuery = !query || haystack.includes(query);
        return matchesStatus && matchesCustomer && matchesYear && matchesQuery;
    });
}

function renderCustomerOptions() {
    const filter = document.getElementById("payment-customer-filter");
    const editor = document.getElementById("payment-customer");
    if (!filter || !editor) {
        return;
    }

    filter.innerHTML = ['<option value="all">All Customers</option>', ...paymentsState.customers.map((customer) => `<option value="${customer.id}">${customer.customer_name}</option>`)].join("");
    filter.value = paymentsState.customerFilter;
    editor.innerHTML = paymentsState.customers.map((customer) => `<option value="${customer.id}">${customer.customer_name}</option>`).join("");
}

function renderYearOptions() {
    const filter = document.getElementById("payment-year-filter");
    if (!filter) {
        return;
    }
    const years = Array.from(new Set(paymentsState.payments.map((payment) => String(payment.payment_date).slice(0, 4)))).sort().reverse();
    filter.innerHTML = ['<option value="all">All Years</option>', ...years.map((year) => `<option value="${year}">${year}</option>`)].join("");
    filter.value = paymentsState.yearFilter;
}

function renderMetrics(payments) {
    const visibleReceipts = payments.reduce((sum, payment) => sum + payment.amount_cents, 0);
    const appliedAmount = payments.reduce((sum, payment) => sum + payment.applied_amount_cents, 0);
    const unappliedAmount = payments.reduce((sum, payment) => sum + payment.unapplied_amount_cents, 0);

    setText("payments-mode", paymentsState.isLoading ? "Loading" : "Served Mode");
    setText("metric-visible-receipts", currency(visibleReceipts));
    setText("metric-applied-amount", currency(appliedAmount));
    setText("metric-unapplied-amount", currency(unappliedAmount));
    setText("metric-payment-count", String(payments.length));
}

function renderStatusFilters() {
    document.querySelectorAll("[data-payment-status-filter]").forEach((button) => {
        const isActive = button.dataset.paymentStatusFilter === paymentsState.statusFilter;
        button.classList.toggle("bg-brand", isActive);
        button.classList.toggle("text-stone-50", isActive);
        button.classList.toggle("border-brand", isActive);
        button.classList.toggle("shadow-sm", isActive);
        button.classList.toggle("bg-panel/70", !isActive);
        button.classList.toggle("text-ink", !isActive);
        button.classList.toggle("border-line", !isActive);
    });
}

function renderPaymentRows(payments) {
    const tbody = document.getElementById("payment-table-body");
    const emptyState = document.getElementById("payment-empty-state");
    if (!tbody || !emptyState) {
        return;
    }

    if (paymentsState.isLoading) {
        tbody.innerHTML = "";
        setEmptyState("Loading payments...");
        emptyState.classList.remove("hidden");
        return;
    }
    if (paymentsState.loadError) {
        window.alert(paymentsState.loadError);
        paymentsState.loadError = "";
    }
    if (payments.length === 0) {
        tbody.innerHTML = "";
        setEmptyState("No payments match the current filter.");
        emptyState.classList.remove("hidden");
        return;
    }

    emptyState.classList.add("hidden");
    tbody.innerHTML = payments.map((payment) => {
        const status = paymentStatusMeta(payment);
        const isSelected = payment.id === paymentsState.selectedPaymentId;
        return `
            <tr class="cursor-pointer border-t border-line/70 ${isSelected ? "bg-brand/5" : "bg-white/30 hover:bg-white/60"}" data-payment-select="${payment.id}">
                <td class="px-4 py-4 align-top font-mono text-sm text-ink">${payment.payment_date}</td>
                <td class="px-4 py-4 align-top text-sm text-ink">${payment.customer_name}</td>
                <td class="px-4 py-4 align-top font-mono text-sm text-ink">${payment.reference_number}</td>
                <td class="px-4 py-4 align-top text-right font-mono text-sm text-ink">${currency(payment.amount_cents)}</td>
                <td class="px-4 py-4 align-top text-right font-mono text-sm text-ink">${currency(payment.unapplied_amount_cents)}</td>
                <td class="px-4 py-4 align-top"><span class="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${status.classes}">${status.label}</span></td>
            </tr>
        `;
    }).join("");

    tbody.querySelectorAll("[data-payment-select]").forEach((row) => {
        row.addEventListener("click", async () => {
            paymentsState.selectedPaymentId = Number(row.dataset.paymentSelect);
            await loadEditor(paymentsState.selectedPaymentId);
        });
    });
}

function renderApplications(payment) {
    const currentList = document.getElementById("current-applications-list");
    const openList = document.getElementById("open-invoices-list");
    if (!currentList || !openList) {
        return;
    }

    const applications = paymentsState.editor.applications || [];
    if (applications.length === 0) {
        currentList.innerHTML = '<p class="rounded-xl border border-dashed border-line bg-panel/35 px-3 py-3 text-sm text-muted">No invoice applications saved yet.</p>';
    } else {
        currentList.innerHTML = applications.map((application) => {
            const invoice = (paymentsState.editor.open_invoices || []).find((row) => row.id === application.invoice_id) || { status: "pending" };
            const status = invoiceStatusMeta(invoice);
            return `
                <div class="rounded-xl border border-line bg-panel/35 px-3 py-3">
                    <div class="flex items-start justify-between gap-3">
                        <div>
                            <p class="font-mono text-xs text-ink">${application.invoice_number}</p>
                            <p class="mt-1 text-sm text-ink">Applied on ${String(application.applied_at).slice(0, 10)}</p>
                        </div>
                        <span class="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${status.classes}">${status.label}</span>
                    </div>
                    <p class="mt-2 font-mono text-sm text-ink">${currency(application.applied_amount_cents)}</p>
                </div>
            `;
        }).join("");
    }

    const openInvoices = paymentsState.editor.open_invoices || [];
    setText("open-invoices-count", `${openInvoices.length} rows`);
    if (openInvoices.length === 0) {
        openList.innerHTML = '<p class="rounded-xl border border-dashed border-line bg-panel/35 px-3 py-3 text-sm text-muted">No open invoices for this customer.</p>';
        return;
    }

    openList.innerHTML = openInvoices.map((invoice) => {
        const status = invoiceStatusMeta(invoice);
        const appliedDraft = paymentsState.applicationDrafts[invoice.id];
        return `
            <div class="rounded-xl border border-line bg-panel/35 px-3 py-3">
                <div class="flex items-start justify-between gap-3">
                    <div>
                        <p class="font-mono text-xs text-ink">${invoice.invoice_number}</p>
                        <p class="mt-1 text-sm text-ink">Invoice Date ${invoice.invoice_date}</p>
                    </div>
                    <span class="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${status.classes}">${status.label}</span>
                </div>
                <div class="mt-3 grid gap-3 sm:grid-cols-[minmax(0,1fr)_8rem] sm:items-end">
                    <div>
                        <p class="text-[11px] uppercase tracking-[0.16em] text-muted">Available to Apply</p>
                        <p class="mt-1 font-mono text-sm text-ink">${currency(invoice.available_to_apply_cents)}</p>
                    </div>
                    <div>
                        <label class="text-[11px] uppercase tracking-[0.16em] text-muted" for="application-${invoice.id}">Apply</label>
                        <input class="mt-1 w-full rounded-xl border border-line bg-white px-3 py-2 font-mono text-sm text-ink outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20" data-application-input="${invoice.id}" id="application-${invoice.id}" min="0" step="0.01" type="number" value="${dollarsInput(Number.isFinite(appliedDraft) ? appliedDraft : (invoice.current_applied_cents || 0))}">
                    </div>
                </div>
            </div>
        `;
    }).join("");

    openList.querySelectorAll("[data-application-input]").forEach((input) => {
        input.addEventListener("input", () => {
            updateApplicationDraft(Number(input.dataset.applicationInput), centsFromInput(input.value), input);
        });
    });
}

function updateEditor(payment) {
    const preview = paymentPreview(payment);
    const status = paymentStatusMetaFromStatus(preview.application_status);
    const chip = document.getElementById("payment-editor-status-chip");
    if (chip) {
        chip.className = `rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${status.classes}`;
        chip.textContent = status.label;
    }

    document.getElementById("payment-customer").value = String(payment.customer_id);
    document.getElementById("payment-date").value = payment.payment_date;
    document.getElementById("payment-reference").value = payment.reference_number;
    document.getElementById("payment-amount").value = dollarsInput(payment.amount_cents);
    document.getElementById("payment-notes").value = payment.notes || "";

    ["payment-customer", "payment-date", "payment-reference", "payment-amount", "payment-notes"].forEach((id) => {
        const element = document.getElementById(id);
        if (element) {
            element.disabled = paymentsState.isSaving;
        }
    });

    setText("payment-editor-title", `${payment.reference_number} · ${payment.payment_date}`);
    setText("payment-detail-customer", payment.customer_name);
    setText("payment-detail-amount", currency(payment.amount_cents));
    setText("payment-detail-unapplied", currency(preview.unapplied_amount_cents));
    setText("payment-summary-applied", currency(preview.applied_amount_cents));
    setText("payment-summary-unapplied", currency(preview.unapplied_amount_cents));
    setText("payment-summary-status", status.label);

    renderApplications(payment);
}

function paymentPayloadFromForm(currentPayment) {
    const customerValue = document.getElementById("payment-customer")?.value;
    const dateValue = document.getElementById("payment-date")?.value;
    const referenceValue = document.getElementById("payment-reference")?.value;
    const amountValue = document.getElementById("payment-amount")?.value;
    const notesValue = document.getElementById("payment-notes")?.value;
    return {
        customer_id: Number(customerValue ?? currentPayment?.customer_id ?? 0),
        payment_date: String(dateValue ?? currentPayment?.payment_date ?? TODAY),
        reference_number: String(referenceValue ?? currentPayment?.reference_number ?? "").trim(),
        amount_cents: amountValue === undefined
            ? (currentPayment?.amount_cents || 0)
            : centsFromInput(amountValue),
        notes: String(notesValue ?? currentPayment?.notes ?? "")
    };
}

function syncSelectedPaymentFromForm(clearApplicationsOnCustomerChange = false) {
    const payment = selectedPayment();
    if (!payment) {
        return;
    }

    const previousCustomerId = payment.customer_id;
    const payload = paymentPayloadFromForm(payment);
    const customer = customerById(payload.customer_id);
    payment.customer_id = payload.customer_id;
    payment.customer_name = customer?.customer_name || payment.customer_name;
    payment.payment_date = payload.payment_date;
    payment.reference_number = payload.reference_number;
    payment.amount_cents = payload.amount_cents;
    payment.notes = payload.notes;

    if (clearApplicationsOnCustomerChange && previousCustomerId !== payload.customer_id) {
        paymentsState.editor.applications = [];
        paymentsState.editor.open_invoices = [];
        paymentsState.applicationDrafts = {};
    }
}

async function createDraftPayment(sourcePayment = null) {
    if (paymentsState.isSaving) {
        return;
    }
    const customer = sourcePayment ? customerById(sourcePayment.customer_id) : paymentsState.customers[0];
    if (!customer) {
        return;
    }

    paymentsState.selectedPaymentId = null;
    paymentsState.editor = {
        payment: createUnsavedPayment(customer, sourcePayment),
        applications: [],
        open_invoices: []
    };
    paymentsState.applicationDrafts = {};
    paymentsState.loadError = "";
    render();
    await loadCustomerOpenInvoices(customer.id);
}

function updateApplicationDraft(invoiceId, requestedCents, input = null) {
    const payment = selectedPayment();
    if (!payment) {
        return;
    }

    syncSelectedPaymentFromForm();
    const openInvoices = paymentsState.editor.open_invoices || [];
    const invoice = openInvoices.find((row) => row.id === invoiceId);
    if (!invoice) {
        return;
    }

    const otherApplied = openInvoices.reduce((sum, row) => {
        if (row.id === invoiceId) {
            return sum;
        }
        const draft = paymentsState.applicationDrafts[row.id];
        return sum + (Number.isFinite(draft) ? draft : (row.current_applied_cents || 0));
    }, 0);
    const maxForPayment = Math.max(0, payment.amount_cents - otherApplied);
    const nextAmount = Math.max(0, Math.min(requestedCents, invoice.available_to_apply_cents, maxForPayment));
    paymentsState.applicationDrafts[invoiceId] = nextAmount;
    if (input && nextAmount !== requestedCents) {
        input.value = dollarsInput(nextAmount);
    }
    updatePaymentSummary(payment);
}

async function savePayment() {
    const payment = selectedPayment();
    if (!payment || paymentsState.isSaving) {
        return;
    }

    paymentsState.isSaving = true;
    render();
    try {
        const isSavedPayment = Boolean(payment.id);
        const existingPayment = isSavedPayment
            ? paymentsState.payments.find((currentPayment) => currentPayment.id === payment.id)
            : null;
        if (isSavedPayment && existingPayment && existingPayment.customer_id === payment.customer_id) {
            await saveApplicationsForPayment(payment.id);
        }

        const data = await requestJson(
            isSavedPayment ? `/${payment.id}` : "",
            {
                method: isSavedPayment ? "PUT" : "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(paymentPayloadFromForm(payment))
            },
            "Unable to save payment."
        );
        if (data.payment) {
            upsertPayment(data.payment);
            await saveApplicationsForPayment(data.payment.id);
            await loadEditor(data.payment.id);
        }
        paymentsState.loadError = "";
    } catch (error) {
        paymentsState.loadError = "";
        window.alert(extractErrorMessage(error, "Unable to save payment."));
    } finally {
        paymentsState.isSaving = false;
        render();
    }
}

function applicationPayloadFromDrafts() {
    return (paymentsState.editor.open_invoices || [])
        .map((invoice) => ({
            invoice_id: invoice.id,
            applied_amount_cents: Number.isFinite(paymentsState.applicationDrafts[invoice.id])
                ? paymentsState.applicationDrafts[invoice.id]
                : (invoice.current_applied_cents || 0)
        }))
        .filter((application) => application.applied_amount_cents > 0);
}

async function saveApplicationsForPayment(paymentId) {
    if (!paymentId) {
        return null;
    }
    return requestJson(
        `/${paymentId}/applications`,
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ applications: applicationPayloadFromDrafts() })
        },
        "Unable to save payment applications."
    );
}

async function deleteSelectedPayment() {
    const payment = selectedPayment();
    if (!payment || paymentsState.isSaving) {
        return;
    }

    if (!payment.id) {
        paymentsState.editor = { payment: null, applications: [], open_invoices: [] };
        paymentsState.applicationDrafts = {};
        paymentsState.selectedPaymentId = paymentsState.payments[0]?.id || null;
        await loadEditor(paymentsState.selectedPaymentId);
        return;
    }

    paymentsState.isSaving = true;
    render();
    try {
        await requestJson(
            `/${payment.id}`,
            { method: "DELETE" },
            "Unable to delete payment."
        );
        paymentsState.payments = paymentsState.payments.filter((currentPayment) => currentPayment.id !== payment.id);
        paymentsState.editor = { payment: null, applications: [], open_invoices: [] };
        paymentsState.applicationDrafts = {};
        paymentsState.selectedPaymentId = paymentsState.payments[0]?.id || null;
        await loadEditor(paymentsState.selectedPaymentId);
        paymentsState.loadError = "";
    } catch (error) {
        window.alert(extractErrorMessage(error, "Unable to delete payment."));
    } finally {
        paymentsState.isSaving = false;
        render();
    }
}

function bindEvents() {
    document.getElementById("payment-search")?.addEventListener("input", (event) => {
        paymentsState.searchQuery = event.target.value;
        render();
    });

    document.getElementById("payment-customer-filter")?.addEventListener("change", (event) => {
        paymentsState.customerFilter = event.target.value;
        render();
    });

    document.getElementById("payment-year-filter")?.addEventListener("change", (event) => {
        paymentsState.yearFilter = event.target.value;
        render();
    });

    document.querySelectorAll("[data-payment-status-filter]").forEach((button) => {
        button.addEventListener("click", () => {
            paymentsState.statusFilter = button.dataset.paymentStatusFilter || "all";
            render();
        });
    });

    document.getElementById("new-payment-button")?.addEventListener("click", () => {
        void createDraftPayment(null);
    });
    document.getElementById("save-payment-button")?.addEventListener("click", savePayment);
    document.getElementById("delete-payment-button")?.addEventListener("click", () => {
        void deleteSelectedPayment();
    });
    document.getElementById("reset-payment-filters-button")?.addEventListener("click", () => {
        paymentsState.searchQuery = "";
        paymentsState.customerFilter = "all";
        paymentsState.yearFilter = "all";
        paymentsState.statusFilter = "all";
        const search = document.getElementById("payment-search");
        if (search) {
            search.value = "";
        }
        render();
    });

    document.getElementById("payment-customer")?.addEventListener("change", async () => {
        syncSelectedPaymentFromForm(true);
        await loadCustomerOpenInvoices(Number(document.getElementById("payment-customer")?.value || 0));
    });
    document.getElementById("payment-date")?.addEventListener("input", () => {
        syncSelectedPaymentFromForm();
        updatePaymentHeader(selectedPayment());
    });
    document.getElementById("payment-reference")?.addEventListener("input", () => {
        syncSelectedPaymentFromForm();
        updatePaymentHeader(selectedPayment());
    });
    document.getElementById("payment-amount")?.addEventListener("input", () => {
        syncSelectedPaymentFromForm();
        updatePaymentHeader(selectedPayment());
    });
    document.getElementById("payment-notes")?.addEventListener("input", () => {
        syncSelectedPaymentFromForm();
        updatePaymentHeader(selectedPayment());
    });
}

function render() {
    renderNavState();
    renderCustomerOptions();
    renderYearOptions();
    renderStatusFilters();

    const payments = filteredPayments();
    renderMetrics(payments);
    renderPaymentRows(payments);

    const payment = paymentsState.editor.payment || selectedPayment();
    if (payment) {
        updateEditor(payment);
    }
}

window.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    render();
    loadPayments();
});
