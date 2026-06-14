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
    setText("company-mode", companyState.isLoading ? "Loading..." : (companyState.profile?.company_name || "Ready"));
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
    renderNavState();
    bindEvents();
    loadCompanyProfile();
});
