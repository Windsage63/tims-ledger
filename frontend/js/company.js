/**
 * @fileoverview Edit the company profile and preview printed invoice identity.
 * @license Apache-2.0
 * @copyright 2026 Timothy Mallory
 */

const companyState = {
    profile: null,
    isLoading: true,
    isSaving: false,
    statusMessage: "Loading company profile...",
    statusKind: "info"
};

function companyUrl(path = "") {
    return `/api/company${path}`;
}

async function requestJson(path, options = {}, fallbackMessage = "Request failed.") {
    return apiRequestJson(companyUrl(), path, options, fallbackMessage);
}

function setStatus(message, kind = "info") {
    companyState.statusMessage = message;
    companyState.statusKind = kind;
    const element = document.getElementById("company-status");
    if (!element) {
        return;
    }
    element.textContent = message;
    element.classList.toggle("text-danger", kind === "error");
    element.classList.toggle("text-branddeep", kind === "success");
    element.classList.toggle("text-muted", kind === "info");
}

function formPayload() {
    return {
        company_name: String(document.getElementById("company-name")?.value || ""),
        street_address: String(document.getElementById("street-address")?.value || ""),
        city: String(document.getElementById("city")?.value || ""),
        state: String(document.getElementById("state")?.value || ""),
        zip: String(document.getElementById("zip")?.value || ""),
        email: String(document.getElementById("email")?.value || ""),
        phone: String(document.getElementById("phone")?.value || "")
    };
}

function fillForm(profile) {
    document.getElementById("company-name").value = profile.company_name || "";
    document.getElementById("street-address").value = profile.street_address || "";
    document.getElementById("city").value = profile.city || "";
    document.getElementById("state").value = profile.state || "";
    document.getElementById("zip").value = profile.zip || "";
    document.getElementById("email").value = profile.email || "";
    document.getElementById("phone").value = profile.phone || "";
}

function renderPreview(profile) {
    setText("preview-company-name", profile?.company_name || "Company Profile");
    setHtml(
        "preview-address",
        profile
            ? `${escapeHtml(profile.street_address)}<br>${escapeHtml(profile.city)}, ${escapeHtml(profile.state)} ${escapeHtml(profile.zip)}`
            : "-"
    );
    setHtml(
        "preview-contact",
        profile
            ? `Email: ${escapeHtml(profile.email)}<br>Phone: ${escapeHtml(profile.phone)}`
            : "-"
    );
    setText("preview-payable", profile ? `Make all checks payable to ${profile.company_name}` : "-");
}

function render() {
    if (companyState.profile) {
        fillForm(companyState.profile);
    }
    renderPreview(companyState.profile);
    setStatus(companyState.statusMessage, companyState.statusKind);
}

async function loadCompanyProfile() {
    companyState.isLoading = true;
    companyState.statusMessage = "Loading company profile...";
    companyState.statusKind = "info";
    render();

    try {
        const data = await requestJson("/profile", {}, "Unable to load company profile.");
        companyState.profile = data.profile || null;
        companyState.statusMessage = "Company profile loaded.";
        companyState.statusKind = "success";
    } catch (error) {
        companyState.profile = null;
        companyState.statusMessage = extractErrorMessage(error, "Unable to load company profile.");
        companyState.statusKind = "error";
    } finally {
        companyState.isLoading = false;
        render();
    }
}

async function saveCompanyProfile() {
    companyState.isSaving = true;
    setStatus("Saving company profile...", "info");

    try {
        const data = await requestJson(
            "/profile",
            {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(formPayload())
            },
            "Unable to save company profile."
        );
        companyState.profile = data.profile || null;
        companyState.statusMessage = "Company profile saved.";
        companyState.statusKind = "success";
    } catch (error) {
        companyState.statusMessage = extractErrorMessage(error, "Unable to save company profile.");
        companyState.statusKind = "error";
    } finally {
        companyState.isSaving = false;
        render();
    }
}

function bindEvents() {
    document.getElementById("company-form")?.addEventListener("submit", (event) => {
        event.preventDefault();
        saveCompanyProfile();
    });
    document.getElementById("save-company-button")?.addEventListener("click", () => {
        saveCompanyProfile();
    });
    document.getElementById("reload-company-button")?.addEventListener("click", () => {
        loadCompanyProfile();
    });
}

window.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    loadCompanyProfile();
    bindSettingsBackupEvents();
    renderSettingsBackups();
});

function renderSettingsBackups() {
    const select = document.getElementById("backup-select");
    const previous = select.value;
    select.innerHTML = shellBackups.backups.length
        ? shellBackups.backups.map((backup) => `<option value="${escapeHtml(backup.file_name)}">${escapeHtml(backup.file_name)} · ${escapeHtml(backupTimestamp(backup.created_at))}</option>`).join("")
        : '<option value="">No backups available</option>';
    if (shellBackups.backups.some((backup) => backup.file_name === previous)) select.value = previous;
    select.disabled = shellBackups.busy || shellBackups.backups.length === 0;
    document.getElementById("create-backup-button").disabled = shellBackups.busy || Date.now() < shellBackups.cooldownUntil;
    document.getElementById("restore-backup-button").disabled = shellBackups.busy || shellBackups.backups.length === 0;
    setText("backup-status", shellBackups.error || (shellBackups.busy ? "Working…" : `${shellBackups.backups.length} backups available.`));
}

async function restoreSettingsBackup() {
    const fileName = document.getElementById("backup-select").value;
    if (!fileName || shellBackups.busy) return;
    if (!window.confirm(`Restore ${fileName}? This replaces the current database and saved invoices. A safety backup of the current data will be created first.`)) return;
    shellBackups.busy = true;
    renderShellBackups();
    try {
        await apiRequestJson("/api/backups", "/restore", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_name: fileName })
        }, "Unable to restore backup.");
        // Reload all current page state after the database and documents change.
        window.location.reload();
    } catch (error) {
        showToast(error.message);
    } finally {
        shellBackups.busy = false;
        renderShellBackups();
    }
}

function bindSettingsBackupEvents() {
    window.addEventListener("backups:changed", renderSettingsBackups);
    document.getElementById("create-backup-button").addEventListener("click", () => void createShellBackup());
    document.getElementById("restore-backup-button").addEventListener("click", () => void restoreSettingsBackup());
}
