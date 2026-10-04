/**
 * @fileoverview Provide shared formatting, escaping, DOM, and JSON request helpers.
 * @license Apache-2.0
 * @copyright 2026 Timothy Mallory
 */

function currency(cents) {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format((cents || 0) / 100);
}

function money(cents) {
    return currency(cents);
}

function formatCurrency(cents) {
    return currency(cents);
}

function dollarsInput(cents) {
    return ((cents || 0) / 100).toFixed(2);
}

function centsFromInput(value) {
    return Math.round(Number(value || 0) * 100);
}

function todayDateInputValue(date = new Date()) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (!element) {
        return;
    }
    element.textContent = value;
}

function setHtml(id, value) {
    const element = document.getElementById(id);
    if (!element) {
        return;
    }
    element.innerHTML = value;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function extractErrorMessage(error, fallbackMessage) {
    if (!error) {
        return fallbackMessage;
    }
    if (typeof error === "string") {
        return error;
    }
    if (error.errors?.length) {
        return error.errors[0].message || fallbackMessage;
    }
    if (error.detail) {
        if (typeof error.detail === "string") {
            return error.detail;
        }
        if (Array.isArray(error.detail) && error.detail.length > 0) {
            return error.detail.map(formatValidationError).join(" ");
        }
    }
    if (error.message) {
        return error.message;
    }
    return fallbackMessage;
}

function formatValidationError(item) {
    if (!item || typeof item !== "object") {
        return String(item);
    }

    const message = String(item.msg || item.message || item).replace(/^Value error,\s*/i, "");
    const location = Array.isArray(item.loc) ? item.loc : [];
    const field = location[location.length - 1];
    if (!field || field === "body") {
        return message;
    }

    return `${fieldLabel(field)}: ${message}`;
}

function fieldLabel(fieldName) {
    const labels = {
        amount_cents: "Amount",
        applied_amount_cents: "Applied amount",
        customer_id: "Customer",
        invoice_id: "Invoice",
        notes: "Notes",
        payment_date: "Payment Date",
        reference_number: "Reference No."
    };
    if (labels[fieldName]) {
        return labels[fieldName];
    }
    return String(fieldName)
        .replace(/_id$/, "")
        .replace(/_cents$/, "")
        .replaceAll("_", " ")
        .replace(/\b\w/g, (character) => character.toUpperCase());
}

async function apiRequestJson(apiRoot, path = "", options = {}, fallbackMessage = "Request failed.") {
    const response = await fetch(`${apiRoot}${path}`, {
        ...options,
        headers: {
            Accept: "application/json",
            ...(options.headers || {})
        }
    });
    const payload = await response.json();
    if (!response.ok) {
        const error = new Error(extractErrorMessage(payload, fallbackMessage));
        error.httpStatus = response.status;
        throw error;
    }
    return payload.data || {};
}

function showToast(message, kind = "error") {
    const region = document.getElementById("toast-region");
    if (!region) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${kind}`;
    const text = document.createElement("span");
    text.textContent = String(message);
    const dismiss = document.createElement("button");
    dismiss.type = "button";
    dismiss.textContent = "×";
    dismiss.setAttribute("aria-label", "Dismiss notification");
    dismiss.addEventListener("click", () => toast.remove());
    toast.append(text, dismiss);
    region.append(toast);
    window.setTimeout(() => toast.remove(), kind === "error" ? 15000 : 6000);
}

function syncFilterButtons(selector, attribute, value) {
    document.querySelectorAll(selector).forEach((button) => {
        const active = button.getAttribute(attribute) === value;
        button.className = "tab";
        button.setAttribute("aria-pressed", String(active));
    });
}

const newRecordListeners = new Set();

function consumeNewRecordRequest(buttonId) {
    if (!newRecordListeners.has(buttonId)) {
        newRecordListeners.add(buttonId);
        window.addEventListener("hashchange", () => consumeNewRecordRequest(buttonId));
    }
    if (window.location.hash !== "#new") return;
    const button = document.getElementById(buttonId);
    if (!button || button.disabled) return;
    button.click();
    history.replaceState(null, "", window.location.pathname + window.location.search);
}

function invoiceTermsLabel(days) {
    return Number(days) === 0 ? "Due on receipt" : `Net ${Number(days)}`;
}

// Work with calendar dates, avoiding timezone shifts and daylight-saving offsets.
function invoiceDueDate(invoice) {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(invoice?.invoice_date || ""));
    if (!match) return "";
    const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
    if (date.toISOString().slice(0, 10) !== match[0]) return "";
    const terms = Number(invoice.terms_days ?? 30);
    if (!Number.isInteger(terms) || terms < 0) return "";
    date.setUTCDate(date.getUTCDate() + terms);
    if (!Number.isFinite(date.getTime())) return "";
    return date.toISOString().slice(0, 10);
}

function isInvoiceOverdue(invoice, today = todayDateInputValue()) {
    return invoiceOverdueDays(invoice, today) > 0;
}

function invoiceOverdueDays(invoice, today = todayDateInputValue()) {
    if (!["printed", "pending"].includes(invoice?.status) || !(Number(invoice.open_balance_cents) > 0)) return 0;
    const due = invoiceDueDate(invoice);
    const validToday = invoiceDueDate({ invoice_date: today, terms_days: 0 });
    if (!due || !validToday) return 0;
    return Math.max(0, Math.round((Date.parse(`${validToday}T00:00:00Z`) - Date.parse(`${due}T00:00:00Z`)) / 86400000));
}

function invoiceDisplayStatus(invoice, today = todayDateInputValue()) {
    if (invoice?.status === "paid") return { key: "paid", label: "Paid", classes: "status-paid" };
    if (!["printed", "pending"].includes(invoice?.status)) return { key: "draft", label: "Draft", classes: "status-draft" };
    const days = invoiceOverdueDays(invoice, today);
    if (!days) return { key: "printed", label: "Open", classes: "status-open" };
    return { key: "overdue", label: `Overdue ${days} ${days === 1 ? "day" : "days"}`, classes:
        days <= 30 ? "status-overdue-30" : days <= 60 ? "status-overdue-60" : days <= 90 ? "status-overdue-90" : "status-overdue-old" };
}

// Repaint age-sensitive displays without loading or replacing browser drafts.
function onInvoiceCalendarChange(callback) {
    let day = todayDateInputValue();
    const check = () => {
        const next = todayDateInputValue();
        if (next !== day) { day = next; callback(); }
    };
    window.setInterval(check, 30000);
    window.addEventListener("focus", check);
    document.addEventListener("visibilitychange", check);
}
