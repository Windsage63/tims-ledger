const timeState = {
    projects: [],
    entries: [],
    searchQuery: "",
    statusFilter: "all",
    projectFilter: "all",
    yearFilter: "all",
    selectedId: null,
    draftEntry: null,
    isLoading: true,
    isSaving: false,
    loadError: ""
};

const TIME_BOOTSTRAP_TIMEOUT_MS = 8000;

function timeUrl(path = "") {
    return `/api/time${path}`;
}

function timeEntriesUrl(path = "") {
    return `/api/time-entries${path}`;
}

function formatHours(hours) {
    const rounded = Math.round((hours || 0) * 100) / 100;
    return String(rounded).replace(/\.0+$/, "").replace(/(\.\d*[1-9])0+$/, "$1");
}

function hoursFromMinutes(minutes) {
    return formatHours((minutes || 0) / 60);
}

function minutesFromHours(hoursValue) {
    const hours = Number(hoursValue || 0);
    if (!Number.isFinite(hours) || hours <= 0) {
        return 0;
    }

    return Math.round(hours * 4) * 15;
}

function setEmptyState(title, message) {
    const emptyState = document.getElementById("time-empty-state");
    if (!emptyState) {
        return;
    }

    emptyState.innerHTML = `
        <p class="font-display text-2xl font-bold text-ink">${title}</p>
        <p class="mt-2 text-sm leading-6 text-muted">${message}</p>
    `;
}

function timeBootstrapErrorMessage(error) {
    if (error?.name === "AbortError") {
        return "Timed out waiting for the time API. Confirm the FastAPI server is running, then reload the page.";
    }

    if (error instanceof TypeError) {
        return "The time API is unavailable from this page. Open the app through FastAPI instead of loading the HTML file directly.";
    }

    return error instanceof Error ? error.message : "Unable to load time entries.";
}

function projectById(projectId) {
    return timeState.projects.find((project) => project.id === Number(projectId)) || null;
}

function rateForProject(projectId, rateCode) {
    const project = projectById(projectId);
    return project?.rates.find((rate) => rate.rate_code === rateCode) || null;
}

function entryStatusMeta(entry) {
    if (entry.invoice_number) {
        return { label: "Invoiced", classes: "bg-calm/10 text-calm border border-calm/20" };
    }
    if ((entry.rate_cents || 0) === 0) {
        return { label: "Non-Billable", classes: "bg-stone-200/70 text-stone-700 border border-stone-300" };
    }
    return { label: "Unbilled", classes: "bg-brand/10 text-brand border border-brand/20" };
}

function emptyTimeDraft(overrides = {}) {
    const firstProject = timeState.projects[0];
    const firstRate = firstProject?.rates[0];
    return {
        id: "",
        entry_date: todayDateInputValue(),
        project_id: firstProject?.id || "",
        project_number: firstProject?.project_number || "",
        project_description: firstProject?.description || "",
        customer_id: firstProject?.customer_id || "",
        customer_name: firstProject?.customer_name || "",
        description: "",
        minutes: 60,
        rate_code: firstRate?.rate_code || "",
        rate_cents: firstRate?.rate_cents || 0,
        line_total_cents: Math.round((60 * (firstRate?.rate_cents || 0)) / 60),
        invoice_number: null,
        updated_at: new Date().toISOString(),
        ...overrides
    };
}

function normalizedTimeDraft(entry) {
    const fallback = emptyTimeDraft();
    const project = projectById(entry?.project_id) || timeState.projects[0] || null;
    const rate = rateForProject(project?.id, entry?.rate_code) || project?.rates?.[0] || null;
    const minutes = Number(entry?.minutes || fallback.minutes);

    return {
        ...fallback,
        ...entry,
        project_id: project?.id || fallback.project_id,
        project_number: project?.project_number || fallback.project_number,
        project_description: project?.description || fallback.project_description,
        customer_id: project?.customer_id || fallback.customer_id,
        customer_name: project?.customer_name || fallback.customer_name,
        rate_code: rate?.rate_code || fallback.rate_code,
        rate_cents: rate?.rate_cents || 0,
        minutes,
        line_total_cents: Math.round((minutes * (rate?.rate_cents || 0)) / 60)
    };
}

function selectedEntry() {
    return timeState.entries.find((entry) => entry.id === timeState.selectedId) || null;
}

function filteredEntries() {
    const query = timeState.searchQuery.trim().toLowerCase();
    return timeState.entries.filter((entry) => {
        const status = entry.invoice_number ? "invoiced" : (entry.rate_cents === 0 ? "nonbillable" : "unbilled");
        const matchesStatus = timeState.statusFilter === "all" || status === timeState.statusFilter;
        const matchesProject = timeState.projectFilter === "all" || String(entry.project_id) === timeState.projectFilter;
        const entryYear = String(entry.entry_date).slice(0, 4);
        const matchesYear = timeState.yearFilter === "all" || entryYear === timeState.yearFilter;
        const haystack = [entry.project_number, entry.project_description, entry.customer_name, entry.description, entry.rate_code, entry.invoice_number || ""].join(" ").toLowerCase();
        const matchesQuery = !query || haystack.includes(query);
        return matchesStatus && matchesProject && matchesYear && matchesQuery;
    });
}

function renderProjectOptions() {
    const filter = document.getElementById("time-project-filter");
    const editor = document.getElementById("time-project");
    if (!filter || !editor) {
        return;
    }

    filter.innerHTML = ['<option value="all">All Projects</option>', ...timeState.projects.map((project) => `<option value="${project.id}">${escapeHtml(project.project_number)} - ${escapeHtml(project.description)}</option>`)].join("");
    filter.value = timeState.projectFilter;
    editor.innerHTML = timeState.projects.map((project) => `<option value="${project.id}">${escapeHtml(project.project_number)} - ${escapeHtml(project.description)}</option>`).join("");
}

function renderYearOptions() {
    const filter = document.getElementById("time-year-filter");
    if (!filter) {
        return;
    }

    const years = Array.from(new Set(timeState.entries.map((entry) => String(entry.entry_date).slice(0, 4)))).sort().reverse();
    filter.innerHTML = ['<option value="all">All Years</option>', ...years.map((year) => `<option value="${year}">${year}</option>`)].join("");
    filter.value = timeState.yearFilter;
}

function renderMetrics(entries) {
    if (timeState.isLoading) {
        setText("time-mode", "Loading...");
        setText("metric-visible-hours", "-");
        setText("metric-billable-amount", "-");
        setText("metric-unbilled-hours", "-");
        setText("metric-nonbillable-hours", "-");
        return;
    }

    const totalMinutes = entries.reduce((sum, entry) => sum + entry.minutes, 0);
    const billableAmount = entries.reduce((sum, entry) => sum + (entry.rate_cents > 0 ? entry.line_total_cents : 0), 0);
    const unbilledMinutes = entries.reduce((sum, entry) => sum + (!entry.invoice_number ? entry.minutes : 0), 0);
    const nonbillableMinutes = entries.reduce((sum, entry) => sum + (entry.rate_cents === 0 ? entry.minutes : 0), 0);
    setText("time-mode", window.location.protocol === "file:" ? "File Mode" : "SQLite Mode");
    setText("metric-visible-hours", hoursFromMinutes(totalMinutes));
    setText("metric-billable-amount", currency(billableAmount));
    setText("metric-unbilled-hours", hoursFromMinutes(unbilledMinutes));
    setText("metric-nonbillable-hours", hoursFromMinutes(nonbillableMinutes));
}

function renderStatusFilters() {
    document.querySelectorAll("[data-time-status-filter]").forEach((button) => {
        const isActive = button.dataset.timeStatusFilter === timeState.statusFilter;
        button.classList.toggle("bg-brand", isActive);
        button.classList.toggle("text-stone-50", isActive);
        button.classList.toggle("border-brand", isActive);
        button.classList.toggle("shadow-sm", isActive);
        button.classList.toggle("bg-panel/70", !isActive);
        button.classList.toggle("text-ink", !isActive);
        button.classList.toggle("border-line", !isActive);
    });
}

function renderEntryRows(entries) {
    const tbody = document.getElementById("time-table-body");
    const emptyState = document.getElementById("time-empty-state");
    if (!tbody || !emptyState) {
        return;
    }

    if (timeState.isLoading) {
        tbody.innerHTML = "";
        setEmptyState("Loading time entries...", "The time screen is waiting for its bootstrap payload from the API.");
        emptyState.classList.remove("hidden");
        return;
    }

    if (timeState.loadError) {
        tbody.innerHTML = "";
        setEmptyState("Time load failed", timeState.loadError);
        emptyState.classList.remove("hidden");
        return;
    }

    if (entries.length === 0) {
        tbody.innerHTML = "";
        setEmptyState("No time entries match the current filter.", "Adjust the project, year, or status filter, or create a new time draft.");
        emptyState.classList.remove("hidden");
        return;
    }

    emptyState.classList.add("hidden");
    tbody.innerHTML = entries.map((entry) => {
        const status = entryStatusMeta(entry);
        const isSelected = entry.id === timeState.selectedId;
        return `
            <tr class="cursor-pointer border-t border-line/70 ${isSelected ? "bg-brand/5" : "bg-white/30 hover:bg-white/60"}" data-time-select="${entry.id}">
                <td class="px-4 py-4 align-top font-mono text-sm text-ink">${escapeHtml(entry.entry_date)}</td>
                <td class="px-4 py-4 align-top text-sm text-ink">${escapeHtml(entry.project_number)}</td>
                <td class="px-4 py-4 align-top text-sm text-ink">${escapeHtml(entry.customer_name)}</td>
                <td class="px-4 py-4 align-top text-sm text-ink">${escapeHtml(entry.project_description)}</td>
                <td class="px-4 py-4 align-top text-sm text-muted">${escapeHtml(entry.description)}</td>
                <td class="px-4 py-4 align-top text-right font-mono text-sm text-ink">${hoursFromMinutes(entry.minutes)}</td>
                <td class="px-4 py-4 align-top text-sm text-ink">${escapeHtml(entry.rate_code)}</td>
                <td class="px-4 py-4 align-top"><span class="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${status.classes}">${status.label}</span></td>
            </tr>
        `;
    }).join("");

    tbody.querySelectorAll("[data-time-select]").forEach((row) => {
        row.addEventListener("click", () => {
            timeState.selectedId = Number(row.dataset.timeSelect);
            timeState.draftEntry = null;
            render();
        });
    });
}

function renderRateOptions(projectId, selectedCode) {
    const select = document.getElementById("time-rate-code");
    if (!select) {
        return;
    }

    const project = projectById(projectId);
    const rates = project?.rates || [];
    select.innerHTML = rates.map((rate) => `<option value="${rate.rate_code}">${rate.rate_code} · ${currency(rate.rate_cents)}</option>`).join("");
    if (selectedCode && rates.some((rate) => rate.rate_code === selectedCode)) {
        select.value = selectedCode;
    }
}

function updateDerivedPreview(entry) {
    const statusChip = document.getElementById("time-editor-status-chip");
    const status = entryStatusMeta(entry);
    if (statusChip) {
        statusChip.className = `rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${status.classes}`;
        statusChip.textContent = entry.id ? status.label : "Draft";
    }

    const derivedLabel = entry.rate_cents === 0
        ? "Non-billable: selected rate resolves to $0.00, so this entry stays out of invoice selection."
        : entry.invoice_number
            ? `Invoiced on ${entry.invoice_number}. This entry keeps its source linkage.`
            : `Billable: selected rate resolves to ${currency(entry.rate_cents)} and this entry is currently unbilled.`;

    setText("time-editor-title", entry.id ? `Entry ${entry.entry_date}` : "New Time Draft");
    setText("time-detail-customer", entry.customer_name || "None");
    setText("time-detail-rate", currency(entry.rate_cents));
    setText("time-detail-total", currency(entry.line_total_cents));
    setText("time-derived-billing", derivedLabel);
}

function renderEditor(entry) {
    const form = document.getElementById("time-form");
    if (!form) {
        return;
    }

    const current = normalizedTimeDraft(entry || emptyTimeDraft());
    document.getElementById("time-entry-id").value = current.id;
    document.getElementById("time-entry-date").value = current.entry_date;
    document.getElementById("time-project").value = String(current.project_id || "");
    document.getElementById("time-description").value = current.description;
    document.getElementById("time-hours").value = hoursFromMinutes(current.minutes);
    renderRateOptions(current.project_id, current.rate_code);
    document.getElementById("time-rate-code").value = current.rate_code;
    updateDerivedPreview(current);
}

function syncDraftFromForm() {
    const projectId = Number(document.getElementById("time-project")?.value || 0);
    const rateCode = String(document.getElementById("time-rate-code")?.value || "");
    const project = projectById(projectId);
    const rate = rateForProject(projectId, rateCode);
    const minutes = minutesFromHours(document.getElementById("time-hours")?.value);
    const source = timeState.draftEntry || selectedEntry() || emptyTimeDraft();
    timeState.draftEntry = {
        ...source,
        entry_date: String(document.getElementById("time-entry-date")?.value || source.entry_date),
        project_id: projectId,
        project_number: project?.project_number || source.project_number,
        project_description: project?.description || source.project_description,
        customer_id: project?.customer_id || source.customer_id,
        customer_name: project?.customer_name || source.customer_name,
        description: String(document.getElementById("time-description")?.value || source.description),
        minutes,
        rate_code: rateCode,
        rate_cents: rate?.rate_cents || 0,
        line_total_cents: Math.round((minutes * (rate?.rate_cents || 0)) / 60),
        invoice_number: source.invoice_number,
        updated_at: new Date().toISOString()
    };
    renderEditor(timeState.draftEntry);
}

function upsertEntry(entry) {
    const existingIndex = timeState.entries.findIndex((current) => current.id === entry.id);
    if (existingIndex >= 0) {
        timeState.entries.splice(existingIndex, 1, entry);
        return;
    }

    timeState.entries.unshift(entry);
}

function hydrateProjects(projects, ratesByProject) {
    return projects.map((project) => ({
        ...project,
        rates: Array.isArray(ratesByProject?.[project.id])
            ? ratesByProject[project.id].map((rate) => ({ ...rate }))
            : Array.isArray(ratesByProject?.[String(project.id)])
                ? ratesByProject[String(project.id)].map((rate) => ({ ...rate }))
                : []
    }));
}

async function loadEntries() {
    timeState.isLoading = true;
    timeState.loadError = "";
    render();

    if (window.location.protocol === "file:") {
        timeState.projects = [];
        timeState.entries = [];
        timeState.selectedId = null;
        timeState.isLoading = false;
        timeState.loadError = "The time screen needs the FastAPI backend. Start the app with startup.bat, then open the Time screen from the sidebar.";
        render();
        return;
    }

    let timeoutId = null;

    try {
        const supportsAbortController = typeof window.AbortController === "function";
        const controller = supportsAbortController ? new window.AbortController() : null;
        const requestOptions = controller ? { signal: controller.signal } : {};

        if (controller) {
            timeoutId = window.setTimeout(() => controller.abort(), TIME_BOOTSTRAP_TIMEOUT_MS);
        }

        const response = await fetch(timeUrl("/bootstrap"), requestOptions);
        const payload = await response.json();

        if (!response.ok) {
            throw new Error(extractErrorMessage(payload, "Unable to load time entries."));
        }

        const projects = Array.isArray(payload?.data?.projects) ? payload.data.projects : [];
        const ratesByProject = payload?.data?.rates_by_project || {};

        timeState.projects = hydrateProjects(projects, ratesByProject);
        timeState.entries = Array.isArray(payload?.data?.entries) ? payload.data.entries.map((entry) => ({ ...entry })) : [];
        if (timeState.draftEntry) {
            timeState.draftEntry = normalizedTimeDraft(timeState.draftEntry);
        }

        if (timeState.selectedId && !timeState.entries.some((entry) => entry.id === timeState.selectedId)) {
            timeState.selectedId = null;
        }

        if (!timeState.selectedId && timeState.entries.length > 0) {
            timeState.selectedId = timeState.entries[0].id;
        }
    } catch (error) {
        timeState.projects = [];
        timeState.entries = [];
        timeState.selectedId = null;
        timeState.loadError = timeBootstrapErrorMessage(error);
    } finally {
        if (timeoutId !== null) {
            window.clearTimeout(timeoutId);
        }
        timeState.isLoading = false;
        render();
    }
}

async function saveEntry(event) {
    event.preventDefault();

    if (timeState.isSaving) {
        return;
    }

    syncDraftFromForm();
    const entryId = Number(document.getElementById("time-entry-id")?.value || 0);
    const draft = timeState.draftEntry || emptyTimeDraft();
    const payload = {
        entry_date: draft.entry_date,
        project_id: draft.project_id,
        description: draft.description,
        minutes: draft.minutes,
        rate_code: draft.rate_code
    };

    const method = entryId ? "PUT" : "POST";
    const path = entryId ? `/${entryId}` : "";

    try {
        timeState.isSaving = true;
        const response = await fetch(timeEntriesUrl(path), {
            method,
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });
        const responseBody = await response.json();

        if (!response.ok) {
            throw new Error(extractErrorMessage(responseBody, "Unable to save time entry."));
        }

        const saved = responseBody?.data?.entry;
        if (!saved) {
            throw new Error("Time entry save completed without a returned record.");
        }

        upsertEntry(saved);
        timeState.selectedId = saved.id;
        timeState.draftEntry = null;
    } catch (error) {
        window.alert(error instanceof Error ? error.message : "Unable to save time entry.");
    } finally {
        timeState.isSaving = false;
    }

    render();
}

function clearEntryDraft(copyCurrent = false) {
    if (copyCurrent && selectedEntry()) {
        const original = selectedEntry();
        timeState.selectedId = null;
        timeState.draftEntry = emptyTimeDraft({
            entry_date: original.entry_date,
            project_id: original.project_id,
            project_number: original.project_number,
            project_description: original.project_description,
            customer_id: original.customer_id,
            customer_name: original.customer_name,
            description: original.description,
            minutes: original.minutes,
            rate_code: original.rate_code,
            rate_cents: original.rate_cents,
            line_total_cents: original.line_total_cents,
            invoice_number: null
        });
        render();
        return;
    }

    timeState.selectedId = null;
    timeState.draftEntry = emptyTimeDraft();
    render();
}

function bindEvents() {
    document.getElementById("time-search")?.addEventListener("input", (event) => {
        timeState.searchQuery = event.target.value;
        render();
    });
    document.getElementById("time-project-filter")?.addEventListener("change", (event) => {
        timeState.projectFilter = event.target.value;
        render();
    });
    document.getElementById("time-year-filter")?.addEventListener("change", (event) => {
        timeState.yearFilter = event.target.value;
        render();
    });
    document.querySelectorAll("[data-time-status-filter]").forEach((button) => {
        button.addEventListener("click", () => {
            timeState.statusFilter = button.dataset.timeStatusFilter || "all";
            render();
        });
    });
    document.getElementById("time-form")?.addEventListener("submit", saveEntry);
    document.getElementById("new-time-entry-button")?.addEventListener("click", () => clearEntryDraft(false));
    document.getElementById("clear-time-form-button")?.addEventListener("click", () => clearEntryDraft(false));
    document.getElementById("duplicate-time-button")?.addEventListener("click", () => clearEntryDraft(true));
    document.getElementById("reset-time-filters-button")?.addEventListener("click", () => {
        timeState.searchQuery = "";
        timeState.projectFilter = "all";
        timeState.yearFilter = "all";
        timeState.statusFilter = "all";
        const search = document.getElementById("time-search");
        if (search) {
            search.value = "";
        }
        render();
    });
    document.getElementById("time-project")?.addEventListener("change", () => {
        const projectId = Number(document.getElementById("time-project")?.value || 0);
        const project = projectById(projectId);
        renderRateOptions(projectId, project?.rates[0]?.rate_code || "");
        syncDraftFromForm();
    });
    document.getElementById("time-rate-code")?.addEventListener("change", syncDraftFromForm);
    document.getElementById("time-hours")?.addEventListener("input", syncDraftFromForm);
    document.getElementById("time-entry-date")?.addEventListener("input", syncDraftFromForm);
    document.getElementById("time-description")?.addEventListener("input", syncDraftFromForm);
}

function render() {
    renderNavState();
    renderProjectOptions();
    renderYearOptions();
    renderStatusFilters();
    const entries = filteredEntries();
    renderMetrics(entries);
    renderEntryRows(entries);
    const entry = selectedEntry() || timeState.draftEntry;
    renderEditor(entry);
}

window.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    render();
    void loadEntries();
});
