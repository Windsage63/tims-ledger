/**
 * @fileoverview Manage payment drafts and invoice application amounts.
 * @license Apache-2.0
 * @copyright 2026 Timothy Mallory
 */

const paymentsState = {
    customers: [],
    payments: [],
    businessSummary: null,
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
    isEditorLoading: false,
    needsReconcile: false,
    allocationLoadFailed: false,
    creationUncertain: false,
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
        payment_date: todayDateInputValue(),
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

function invoiceStatusMeta(invoice) { return invoiceDisplayStatus(invoice); }

let paymentEditorRequest = 0;
let paymentSaveAuthorized = false;

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
        payment: cloneEditorData(data.payment) || null,
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
    const request = ++paymentEditorRequest;
    paymentsState.isEditorLoading = true;
    render();
    try {
        const data = paymentId ? await requestJson(`/${paymentId}/editor`, {}, "Unable to load payment details.") : {};
        if (request !== paymentEditorRequest) return false;
        setEditorPayload(data);
        paymentsState.selectedPaymentId = data.payment?.id || null;
        paymentsState.needsReconcile = false;
        paymentsState.creationUncertain = false;
        paymentsState.allocationLoadFailed = false;
        render();
        editorProtection.accept();
        return true;
    } catch (error) {
        if (request === paymentEditorRequest) showToast(extractErrorMessage(error, "Unable to load payment details."));
        return false;
    } finally {
        if (request === paymentEditorRequest) { paymentsState.isEditorLoading = false; render(); }
    }
}

async function loadCustomerOpenInvoices(customerId) {
    const request = ++paymentEditorRequest;
    paymentsState.isEditorLoading = true;
    render();
    try {
        const data = customerId ? await requestJson(`/customers/${customerId}/open-invoices`, {}, "Unable to load open invoices.") : {};
        if (request !== paymentEditorRequest || selectedPayment()?.customer_id !== customerId) return false;
        paymentsState.editor.applications = [];
        paymentsState.editor.open_invoices = cloneEditorData(data.open_invoices || []);
        paymentsState.applicationDrafts = Object.fromEntries(paymentsState.editor.open_invoices.map((invoice) => [invoice.id, 0]));
        paymentsState.allocationLoadFailed = false;
        return true;
    } catch (error) {
        if (request === paymentEditorRequest) {
            paymentsState.allocationLoadFailed = true;
            showToast(extractErrorMessage(error, "Unable to load open invoices. Select the customer again before saving."));
        }
        return false;
    } finally {
        if (request === paymentEditorRequest) { paymentsState.isEditorLoading = false; render(); }
    }
}

async function loadPayments() {
    paymentsState.isLoading = true;
    paymentsState.loadError = "";
    render();

    try {
        const data = await requestJson("/bootstrap", {}, "Unable to load payments.");
        paymentsState.customers = Array.isArray(data.customers) ? data.customers : [];
        paymentsState.payments = Array.isArray(data.payments) ? data.payments : [];
        paymentsState.businessSummary = data.business_summary || null;
        paymentsState.selectedPaymentId = paymentsState.payments[0]?.id || null;
        await loadEditor(paymentsState.selectedPaymentId);
    } catch (error) {
        paymentsState.loadError = extractErrorMessage(error, "Unable to load payments.");
        paymentsState.customers = [];
        paymentsState.payments = [];
        paymentsState.businessSummary = null;
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

    filter.innerHTML = ['<option value="all">All Customers</option>', ...paymentsState.customers.map((customer) => `<option value="${customer.id}">${escapeHtml(customer.customer_name)}</option>`)].join("");
    filter.value = paymentsState.customerFilter;
    editor.innerHTML = paymentsState.customers.map((customer) => `<option value="${customer.id}">${escapeHtml(customer.customer_name)}</option>`).join("");
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

function renderMetrics() {
    const summary = paymentsState.businessSummary;
    for (const [id, key] of [
        ["metric-total-income", "total_income_cents"],
        ["metric-open-ar", "total_open_ar_cents"],
        ["metric-total-expenses", "total_expenses_cents"],
        ["metric-non-billable-expenses", "non_billable_expenses_cents"]
    ]) {
        setText(id, Number.isFinite(summary?.[key]) ? currency(summary[key]) : "—");
    }
}

async function refreshBusinessSummary() {
    try {
        const data = await requestJson("/bootstrap", {}, "Unable to refresh business totals.");
        paymentsState.businessSummary = data.business_summary || null;
    } catch (error) {
        paymentsState.businessSummary = null;
        showToast(extractErrorMessage(error, "Unable to refresh business totals."));
    }
    // Updating totals must not replace an editor draft or reset its protection baseline.
    renderMetrics();
}

function renderStatusFilters() {
    syncFilterButtons("[data-payment-status-filter]", "data-payment-status-filter", paymentsState.statusFilter);
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
        showToast(paymentsState.loadError);
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
                <td class="px-4 py-2 align-top font-mono text-sm text-ink">${escapeHtml(payment.payment_date)}</td>
                <td class="px-4 py-2 align-top text-sm text-ink">${escapeHtml(payment.customer_name)}</td>
                <td class="px-4 py-2 align-top font-mono text-sm text-ink">${escapeHtml(payment.reference_number)}</td>
                <td class="px-4 py-2 align-top text-right font-mono text-sm text-ink">${currency(payment.amount_cents)}</td>
                <td class="px-4 py-2 align-top text-right font-mono text-sm text-ink">${currency(payment.unapplied_amount_cents)}</td>
                <td class="px-4 py-2 align-top"><span class="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wide ${status.classes}">${status.label}</span></td>
            </tr>
        `;
    }).join("");

    tbody.querySelectorAll("[data-payment-select]").forEach((row) => {
        row.addEventListener("click", async () => {
            const id = Number(row.dataset.paymentSelect);
            if (id === paymentsState.selectedPaymentId || !editorProtection.allowTransition()) return;
            await loadEditor(id);
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
        currentList.innerHTML = '<p class="rounded border border-dashed border-line bg-panel/35 px-3 py-3 text-sm text-muted">No invoice applications saved yet.</p>';
    } else {
        currentList.innerHTML = applications.map((application) => {
            const invoice = (paymentsState.editor.open_invoices || []).find((row) => row.id === application.invoice_id) || { status: "pending" };
            const status = invoiceStatusMeta(invoice);
            return `
                <div class="rounded border border-line bg-panel/35 px-3 py-3">
                    <div class="flex items-start justify-between gap-3">
                        <div>
                            <p class="font-mono text-xs text-ink">${escapeHtml(application.invoice_number)}</p>
                            <p class="mt-1 text-sm text-ink">Applied on ${escapeHtml(String(application.applied_at).slice(0, 10))}</p>
                        </div>
                        <span class="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wide ${status.classes}">${status.label}</span>
                    </div>
                    <p class="mt-2 font-mono text-sm text-ink">${currency(application.applied_amount_cents)}</p>
                </div>
            `;
        }).join("");
    }

    const openInvoices = paymentsState.editor.open_invoices || [];
    setText("open-invoices-count", `${openInvoices.length} rows`);
    if (openInvoices.length === 0) {
        openList.innerHTML = '<p class="rounded border border-dashed border-line bg-panel/35 px-3 py-3 text-sm text-muted">No open invoices for this customer.</p>';
        return;
    }

    openList.innerHTML = openInvoices.map((invoice) => {
        const status = invoiceStatusMeta(invoice);
        const appliedDraft = paymentsState.applicationDrafts[invoice.id];
        return `
            <div class="rounded border border-line bg-panel/35 px-3 py-3">
                <div class="flex items-start justify-between gap-3">
                    <div>
                        <p class="font-mono text-xs text-ink">${escapeHtml(invoice.invoice_number)}</p>
                        <p class="mt-1 text-sm text-ink">Invoice Date ${escapeHtml(invoice.invoice_date)}</p>
                    </div>
                    <span class="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wide ${status.classes}">${status.label}</span>
                </div>
                <div class="mt-3 grid gap-3 sm:grid-cols-[minmax(0,1fr)_8rem] sm:items-end">
                    <div>
                        <p class="text-[11px] uppercase tracking-[0.16em] text-muted">Available to Apply</p>
                        <p class="mt-1 font-mono text-sm text-ink">${currency(invoice.available_to_apply_cents)}</p>
                    </div>
                    <div>
                        <label class="field-label" for="application-${invoice.id}">Apply</label>
                        <input class="field" data-application-input="${invoice.id}" id="application-${invoice.id}" min="0" step="0.01" type="number" value="${dollarsInput(Number.isFinite(appliedDraft) ? appliedDraft : (invoice.current_applied_cents || 0))}">
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

    setText("payment-editor-title", payment.id ? `${payment.reference_number || "Payment " + payment.id} · ${payment.payment_date}` : "New Payment");
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
        payment_date: String(dateValue ?? currentPayment?.payment_date ?? todayDateInputValue()),
        reference_number: String(referenceValue ?? currentPayment?.reference_number ?? "").trim(),
        amount_cents: amountValue === undefined
            ? (currentPayment?.amount_cents || 0)
            : centsFromInput(amountValue),
        notes: String(notesValue ?? currentPayment?.notes ?? "")
    };
}

function syncSelectedPaymentFromForm(clearApplicationsOnCustomerChange = false) {
    if (!editorProtection.canWrite() || paymentsState.isSaving || paymentsState.isEditorLoading) return;
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
    if (!editorProtection.allowTransition()) return;
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
    paymentsState.needsReconcile = false;
    paymentsState.creationUncertain = false;
    await loadCustomerOpenInvoices(customer.id);
    editorProtection.accept({ lock: true, duplicate: Boolean(sourcePayment) });
}

function updateApplicationDraft(invoiceId, requestedCents, input = null) {
    if (!editorProtection.canWrite() || paymentsState.isSaving || paymentsState.isEditorLoading) return;
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

async function reconcilePaymentDraft() {
    const intended = cloneEditorData({ editor: paymentsState.editor, applicationDrafts: paymentsState.applicationDrafts });
    const id = intended.editor.payment?.id;
    if (!id) return false;
    try {
        const data = await requestJson(`/${id}/editor`, {}, "Unable to reconcile saved payment.");
        if (data.payment.customer_id === intended.editor.payment.customer_id) {
            const availableIds = new Set((data.open_invoices || []).map((invoice) => String(invoice.id)));
            const unavailable = Object.entries(intended.applicationDrafts).find(([invoiceId, cents]) => cents > 0 && !availableIds.has(invoiceId));
            if (unavailable) {
                showToast(`Invoice ${unavailable[0]} is no longer available for this payment. Set its allocation to zero before retrying. Your draft is retained.`);
                throw new Error("An intended allocation is no longer available.");
            }
        }
        setEditorPayload(data);
        render();
        editorProtection.accept();
        // Restore user intent over the persisted baseline, using fresh allocation limits.
        if (data.payment.customer_id === intended.editor.payment.customer_id) {
            intended.editor.open_invoices = cloneEditorData(data.open_invoices || []);
            intended.editor.applications = cloneEditorData(data.applications || []);
        }
        paymentsState.editor = intended.editor;
        paymentsState.applicationDrafts = intended.applicationDrafts;
        paymentsState.needsReconcile = false;
        editorProtection.enableRetry();
        return true;
    } catch (error) {
        paymentsState.editor = intended.editor;
        paymentsState.applicationDrafts = intended.applicationDrafts;
        paymentsState.needsReconcile = true;
        editorProtection.enableRetry();
        return false;
    }
}

async function savePayment() {
    const payment = selectedPayment();
    if (!payment || paymentsState.isSaving || paymentsState.isEditorLoading || !editorProtection.canWrite()) return;
    if (paymentsState.creationUncertain) { showToast("The previous save may have created a payment. Reload this screen and inspect saved payments before creating another."); return; }
    if (paymentsState.allocationLoadFailed) { showToast("Load the customer's invoices before saving. Select the customer again to retry."); return; }
    paymentsState.isSaving = true;
    paymentSaveAuthorized = true;
    render();
    let writeStarted = false;
    try {
        if (paymentsState.needsReconcile && !await reconcilePaymentDraft()) throw new Error("Saved state could not be checked. Your draft is retained; retry when the server is available.");
        const existingPayment = paymentsState.payments.find((entry) => entry.id === payment.id);
        // Release allocations first when reducing a saved amount for the same customer.
        // When increasing it, the payment must be updated before larger allocations fit.
        if (existingPayment && existingPayment.customer_id === payment.customer_id && payment.amount_cents <= existingPayment.amount_cents) {
            await saveApplicationsForPayment(payment.id);
        }
        writeStarted = true;
        const data = await requestJson(payment.id ? `/${payment.id}` : "", {
            method: payment.id ? "PUT" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(paymentPayloadFromForm(payment))
        }, "Unable to save payment.");
        if (!data.payment) throw new Error("Payment save returned no record. Check the payment ledger before retrying.");
        // Keep the new ID immediately; an application failure must never create it again.
        paymentsState.editor.payment.id = data.payment.id;
        paymentsState.selectedPaymentId = data.payment.id;
        upsertPayment(data.payment);
        await saveApplicationsForPayment(data.payment.id);
        const persisted = await requestJson(`/${data.payment.id}/editor`, {}, "Payment saved, but details could not be refreshed.");
        setEditorPayload(persisted);
        paymentsState.needsReconcile = false;
        render();
        editorProtection.saved();
    } catch (error) {
        const id = selectedPayment()?.id;
        if (id) await reconcilePaymentDraft();
        else if (writeStarted && (!error.httpStatus || error.httpStatus >= 500)) {
            paymentsState.creationUncertain = true;
            showToast("The save result is uncertain. Your draft is retained. Reload and inspect saved payments before creating another.");
        }
        showToast(extractErrorMessage(error, "Unable to save payment. Your draft is retained."));
    } finally {
        paymentSaveAuthorized = false;
        paymentsState.isSaving = false;
        render();
        await refreshBusinessSummary();
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
    if (!paymentSaveAuthorized || !paymentsState.isSaving) throw new Error("Use Save Payment with Edit Mode enabled for a saved payment.");
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
    if (!editorProtection.allowTransition()) return;
    const payment = selectedPayment();
    if (!payment || paymentsState.isSaving) {
        return;
    }

    if (!payment.id) {
        if (await loadEditor(paymentsState.payments[0]?.id || null)) editorProtection.saved();
        return;
    }

    if (!editorProtection.canWrite()) return;
    if (!window.confirm(`Delete payment ${payment.reference_number || payment.id}? Its invoice applications will also be removed.`)) return;
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
        editorProtection.saved();
        paymentsState.loadError = "";
    } catch (error) {
        showToast(extractErrorMessage(error, "Unable to delete payment."));
    } finally {
        paymentsState.isSaving = false;
        render();
        await refreshBusinessSummary();
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
        if (!editorProtection.canWrite() || paymentsState.isSaving || paymentsState.isEditorLoading) return;
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
    renderCustomerOptions();
    renderYearOptions();
    renderStatusFilters();

    const payments = filteredPayments();
    renderMetrics();
    renderPaymentRows(payments);

    const payment = paymentsState.editor.payment || selectedPayment();
    if (payment) {
        updateEditor(payment);
    }
    editorProtection.refresh();
}

window.addEventListener("DOMContentLoaded", () => {
    editorProtection.register({
        formId: "payment-form",
        recordId: () => selectedPayment()?.id,
        busy: () => paymentsState.isLoading || paymentsState.isSaving || paymentsState.isEditorLoading,
        snapshot: () => ({ payment: paymentPayloadFromForm(selectedPayment()), applications: applicationPayloadFromDrafts().sort((a, b) => a.invoice_id - b.invoice_id) }),
        capture: () => ({ editor: paymentsState.editor, applicationDrafts: paymentsState.applicationDrafts }),
        restore: (saved) => { paymentsState.editor = saved.editor; paymentsState.applicationDrafts = saved.applicationDrafts; },
        mutationControls: "#save-payment-button, #delete-payment-button, [data-application-input]",
        applyProtection: (blocked) => {
            if (!selectedPayment()) document.querySelectorAll("#payment-form input, #payment-form select, #payment-form textarea, #save-payment-button, #delete-payment-button").forEach((control) => { control.disabled = true; });
            document.getElementById("save-payment-button").disabled = blocked || !selectedPayment() || paymentsState.allocationLoadFailed || paymentsState.creationUncertain;
            if (!selectedPayment()?.id) document.getElementById("delete-payment-button").disabled = paymentsState.isLoading || paymentsState.isSaving || paymentsState.isEditorLoading || !selectedPayment();
        },
        render
    });
    onInvoiceCalendarChange(render);
    document.getElementById("payment-form")?.addEventListener("submit", (event) => { event.preventDefault(); void savePayment(); });
    bindEvents();
    render();
    void loadPayments().then(() => consumeNewRecordRequest("new-payment-button"));
});
