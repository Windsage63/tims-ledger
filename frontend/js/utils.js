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

function getCurrentPage(fallbackPage = "index.html") {
    return window.location.pathname.split("/").pop() || fallbackPage;
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
        throw new Error(extractErrorMessage(payload, fallbackMessage));
    }
    return payload.data || {};
}
