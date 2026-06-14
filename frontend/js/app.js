const reportState = {
    summary: {},
    customers: [],
    selectedCustomerId: null,
    statement: null,
    auditExportPath: "/api/exports/audit.xlsx",
    backups: [],
    selectedBackup: "",
    isBackupBusy: false,
    backupCooldownUntil: 0,
    backupCooldownTimer: null
};

function isBackupCooldownActive() {
    return Date.now() < reportState.backupCooldownUntil;
}

function startBackupCooldown() {
    reportState.backupCooldownUntil = Date.now() + 5000;
    if (reportState.backupCooldownTimer) {
        window.clearTimeout(reportState.backupCooldownTimer);
    }
    reportState.backupCooldownTimer = window.setTimeout(() => {
        reportState.backupCooldownTimer = null;
        renderBackups();
    }, 5000);
}

function renderOverview(data) {
    const summary = data.summary || {};
    const system = data.system || {};
    const isFileMode = window.location.protocol === "file:";

    setText("app-mode", isFileMode ? "File Mode" : "Served Mode");
    setText("metric-sections", String(summary.customers_count ?? "0"));
    setText("metric-mode", String(summary.projects_count ?? "0"));
    setText("metric-next", currency(summary.open_receivables_cents || 0));
    setText("metric-assets", currency(summary.unbilled_work_cents || 0));
}

function renderOverviewError(message) {
    setText("app-mode", "Load Error");
    setText("metric-sections", "-");
    setText("metric-mode", "-");
    setText("metric-next", "-");
    setText("metric-assets", "-");
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

function backupTimestamp(value) {
    if (!value) {
        return "";
    }
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function backupSizeLabel(bytes) {
    const numericBytes = Number(bytes || 0);
    if (numericBytes < 1024) {
        return `${numericBytes} B`;
    }
    if (numericBytes < 1024 * 1024) {
        return `${(numericBytes / 1024).toFixed(1)} KB`;
    }
    return `${(numericBytes / (1024 * 1024)).toFixed(1)} MB`;
}

function setBackupStatus(message) {
    setText("backup-status", message);
}

function renderBackups() {
    const select = document.getElementById("backup-select");
    const createButton = document.getElementById("create-backup-button");
    const restoreButton = document.getElementById("restore-backup-button");
    const backups = Array.isArray(reportState.backups) ? reportState.backups : [];

    if (select) {
        select.innerHTML = backups.length
            ? backups.map((backup) => {
                const label = `${backup.file_name} (${backupSizeLabel(backup.size_bytes)}, ${backupTimestamp(backup.created_at)})`;
                return `<option value="${escapeHtml(backup.file_name)}">${escapeHtml(label)}</option>`;
            }).join("")
            : '<option value="">No backups available</option>';
        if (reportState.selectedBackup && backups.some((backup) => backup.file_name === reportState.selectedBackup)) {
            select.value = reportState.selectedBackup;
        } else {
            select.value = backups[0]?.file_name || "";
            reportState.selectedBackup = select.value;
        }
        select.disabled = reportState.isBackupBusy || backups.length === 0;
    }

    if (createButton) {
        const isCreateDisabled = reportState.isBackupBusy || isBackupCooldownActive();
        createButton.disabled = isCreateDisabled;
        createButton.classList.toggle("opacity-60", isCreateDisabled);
        createButton.textContent = reportState.isBackupBusy ? "Working..." : "Create Backup";
    }

    if (restoreButton) {
        const isDisabled = reportState.isBackupBusy || backups.length === 0;
        restoreButton.disabled = isDisabled;
        restoreButton.classList.toggle("opacity-60", isDisabled);
        restoreButton.textContent = reportState.isBackupBusy ? "Working..." : "Restore Backup";
    }

}

async function requestBackupJson(path, options = {}) {
    return apiRequestJson("", path, options, "Backup request failed.");
}

async function loadBackups() {
    try {
        const data = await requestBackupJson("/api/backups");
        reportState.backups = Array.isArray(data.backups) ? data.backups : [];
        renderBackups();
        setBackupStatus(reportState.backups.length ? `${reportState.backups.length} backups available.` : "No backups yet.");
    } catch (error) {
        reportState.backups = [];
        renderBackups();
        setBackupStatus(error.message || "Unable to load backups.");
    }
}

async function createBackup() {
    if (reportState.isBackupBusy || isBackupCooldownActive()) {
        return;
    }
    reportState.isBackupBusy = true;
    setBackupStatus("Creating backup...");
    renderBackups();
    try {
        const data = await requestBackupJson("/api/backups", { method: "POST" });
        reportState.backups = Array.isArray(data.backups) ? data.backups : [];
        reportState.selectedBackup = data.backup?.file_name || reportState.backups[0]?.file_name || "";
        setBackupStatus(data.backup ? `Created ${data.backup.file_name}.` : "Backup created.");
    } catch (error) {
        setBackupStatus(error.message || "Unable to create backup.");
    } finally {
        startBackupCooldown();
        reportState.isBackupBusy = false;
        renderBackups();
    }
}

async function restoreSelectedBackup() {
    if (reportState.isBackupBusy || !reportState.selectedBackup) {
        return;
    }
    const confirmed = window.confirm(`Restore ${reportState.selectedBackup}? A safety backup of the current database will be created first.`);
    if (!confirmed) {
        return;
    }

    reportState.isBackupBusy = true;
    setBackupStatus("Restoring backup...");
    renderBackups();
    try {
        const data = await requestBackupJson("/api/backups/restore", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_name: reportState.selectedBackup })
        });
        reportState.backups = Array.isArray(data.backups) ? data.backups : [];
        setBackupStatus(`Restored ${data.restored_backup?.file_name || reportState.selectedBackup}. Safety backup: ${data.safety_backup?.file_name || "created"}.`);
        await loadOverview();
        await loadAccountsReceivable();
    } catch (error) {
        setBackupStatus(error.message || "Unable to restore backup.");
    } finally {
        reportState.isBackupBusy = false;
        renderBackups();
    }
}

function renderAccountsReceivable() {
    const summary = reportState.summary || {};
    const customers = Array.isArray(reportState.customers) ? reportState.customers : [];
    const statement = reportState.statement || null;

    setText("ar-total-open", currency(summary.total_open_ar_cents || 0));
    setText("ar-total-credit", currency(summary.total_unapplied_credit_cents || 0));
    setText("ar-total-net", currency(summary.net_receivables_cents || 0));

    const exportLink = document.getElementById("audit-export-link");
    if (exportLink) {
        exportLink.href = reportState.auditExportPath || "/api/exports/audit.xlsx";
    }

    setHtml(
        "ar-customers-body",
        customers.length
            ? customers.map((customer) => `
                <tr class="transition hover:bg-white/70 ${customer.id === reportState.selectedCustomerId ? "bg-brand/10" : ""}">
                    <td class="px-4 py-4">
                        <button class="text-left" data-customer-report-id="${customer.id}" type="button">
                            <p class="font-semibold text-ink">${customer.customer_name}</p>
                            <p class="mt-1 text-xs text-muted">${customer.contact_name} · ${customer.email}</p>
                        </button>
                    </td>
                    <td class="px-4 py-4 font-mono text-sm">${currency(customer.open_ar_cents)}</td>
                    <td class="px-4 py-4 font-mono text-sm">${currency(customer.unapplied_credit_cents)}</td>
                    <td class="px-4 py-4 font-mono text-sm">${currency(customer.net_balance_cents)}</td>
                    <td class="px-4 py-4 text-sm text-muted">${customer.open_invoice_count}</td>
                </tr>`).join("")
            : '<tr><td class="px-4 py-4 text-muted" colspan="5">No customer balance activity is available.</td></tr>'
    );

    if (!statement || !statement.customer) {
        setText("statement-customer-name", "No statement available");
        setText("statement-customer-meta", "Select a customer with current balance activity to review statement detail.");
        setText("statement-open-ar", "-");
        setText("statement-unapplied-credit", "-");
        setText("statement-net-balance", "-");
        setText("statement-generated-at", "-");
        setHtml("statement-invoices-list", '<p class="rounded-2xl border border-line/80 bg-panel/35 px-4 py-4 text-sm text-muted">No printed invoices are available for this customer.</p>');
        setHtml("statement-payments-list", '<p class="rounded-2xl border border-line/80 bg-panel/35 px-4 py-4 text-sm text-muted">No unapplied payments are available for this customer.</p>');
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
                <article class="rounded-2xl border border-line/80 bg-panel/35 px-4 py-4">
                    <div class="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <p class="font-display text-lg font-bold text-ink">${invoice.invoice_number}</p>
                            <p class="mt-1 text-sm text-muted">${invoice.project_number} · ${invoice.invoice_date}</p>
                        </div>
                        <div class="text-right">
                            <p class="font-mono text-sm text-ink">${currency(invoice.invoice_amount_cents)}</p>
                            <p class="mt-1 text-xs uppercase tracking-[0.2em] text-muted">${invoice.status}</p>
                        </div>
                    </div>
                    <div class="mt-3 flex flex-wrap gap-4 text-xs text-muted">
                        <span>Paid ${currency(invoice.paid_amount_cents)}</span>
                        <span>Open ${currency(invoice.open_balance_cents)}</span>
                        <span>Credit ${currency(invoice.unapplied_credit_cents)}</span>
                    </div>
                </article>`).join("")
            : '<p class="rounded-2xl border border-line/80 bg-panel/35 px-4 py-4 text-sm text-muted">No printed invoices are available for this customer.</p>'
    );
    setHtml(
        "statement-payments-list",
        Array.isArray(statement.unapplied_payments) && statement.unapplied_payments.length
            ? statement.unapplied_payments.map((payment) => `
                <article class="rounded-2xl border border-line/80 bg-panel/35 px-4 py-4">
                    <div class="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <p class="font-display text-lg font-bold text-ink">${payment.reference_number || `Payment ${payment.id}`}</p>
                            <p class="mt-1 text-sm text-muted">${payment.payment_date}</p>
                        </div>
                        <div class="text-right">
                            <p class="font-mono text-sm text-ink">${currency(payment.unapplied_amount_cents)}</p>
                            <p class="mt-1 text-xs text-muted">unapplied</p>
                        </div>
                    </div>
                </article>`).join("")
            : '<p class="rounded-2xl border border-line/80 bg-panel/35 px-4 py-4 text-sm text-muted">No unapplied payments are available for this customer.</p>'
    );
}

function renderAccountsReceivableError(message) {
    setText("ar-total-open", "-");
    setText("ar-total-credit", "-");
    setText("ar-total-net", "-");
    setHtml("ar-customers-body", `<tr><td class="px-4 py-4 text-muted" colspan="5">${message}</td></tr>`);
    setText("statement-customer-name", "Load Error");
    setText("statement-customer-meta", message);
    setText("statement-open-ar", "-");
    setText("statement-unapplied-credit", "-");
    setText("statement-net-balance", "-");
    setText("statement-generated-at", "-");
    setHtml("statement-invoices-list", '<p class="rounded-2xl border border-line/80 bg-panel/35 px-4 py-4 text-sm text-muted">Statement data could not be loaded.</p>');
    setHtml("statement-payments-list", '<p class="rounded-2xl border border-line/80 bg-panel/35 px-4 py-4 text-sm text-muted">Statement data could not be loaded.</p>');
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
        reportState.auditExportPath = data.audit_export_path || "/api/exports/audit.xlsx";
        renderAccountsReceivable();
    } catch (error) {
        renderAccountsReceivableError(error.message || "Unable to load accounts receivable report.");
    }
}

function bindNavState() {
    window.addEventListener("hashchange", renderNavState);

    document.querySelectorAll(".side-nav .nav-link").forEach((link) => {
        link.addEventListener("click", () => {
            window.setTimeout(renderNavState, 0);
        });
    });
}

function bindReportingEvents() {
    document.getElementById("ar-customers-body")?.addEventListener("click", (event) => {
        const button = event.target.closest("[data-customer-report-id]");
        if (!button) {
            return;
        }
        void loadAccountsReceivable(button.dataset.customerReportId || null);
    });
    document.getElementById("create-backup-button")?.addEventListener("click", () => {
        void createBackup();
    });
    document.getElementById("backup-select")?.addEventListener("change", (event) => {
        reportState.selectedBackup = event.target.value;
    });
    document.getElementById("restore-backup-button")?.addEventListener("click", () => {
        void restoreSelectedBackup();
    });
}

function bootstrapLandingPage() {
    bindNavState();
    bindReportingEvents();
    renderNavState();
    loadOverview();
    loadAccountsReceivable();
    loadBackups();
}

window.addEventListener("DOMContentLoaded", () => {
    bootstrapLandingPage();
});
