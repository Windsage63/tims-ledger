const projectState = {
    customers: [],
    projects: [],
    searchQuery: "",
    customerFilter: "all",
    selectedId: null,
    draftProject: null,
    isLoading: true,
    isSaving: false,
    loadError: ""
};

function projectsUrl(path = "") {
    return `/api/projects${path}`;
}

function setEmptyState(title, message) {
    const emptyState = document.getElementById("projects-empty-state");
    if (!emptyState) {
        return;
    }

    emptyState.innerHTML = `
        <p class="font-display text-2xl font-bold text-ink">${title}</p>
        <p class="mt-2 text-sm leading-6 text-muted">${message}</p>
    `;
}

function upsertProject(project) {
    const existingIndex = projectState.projects.findIndex((entry) => entry.id === project.id);
    if (existingIndex >= 0) {
        projectState.projects.splice(existingIndex, 1, project);
        return;
    }

    projectState.projects.unshift(project);
}

async function loadProjects() {
    projectState.isLoading = true;
    projectState.loadError = "";
    render();

    try {
        const response = await fetch(projectsUrl("/bootstrap"));
        const payload = await response.json();

        if (!response.ok) {
            throw new Error(extractErrorMessage(payload, "Unable to load projects."));
        }

        projectState.customers = Array.isArray(payload?.data?.customers) ? payload.data.customers : [];
        projectState.projects = Array.isArray(payload?.data?.projects)
            ? payload.data.projects.map((project) => ({
                ...project,
                rates: Array.isArray(project.rates) ? project.rates.map((rate) => ({ ...rate })) : []
            }))
            : [];

        if (projectState.selectedId && !projectState.projects.some((project) => project.id === projectState.selectedId)) {
            projectState.selectedId = null;
        }

        if (!projectState.selectedId && projectState.projects.length > 0) {
            projectState.selectedId = projectState.projects[0].id;
        }
    } catch (error) {
        projectState.customers = [];
        projectState.projects = [];
        projectState.selectedId = null;
        projectState.loadError = error instanceof Error ? error.message : "Unable to load projects.";
    } finally {
        projectState.isLoading = false;
        render();
    }
}

function nextRateId() {
    return Math.max(...projectState.projects.flatMap((project) => project.rates.map((rate) => rate.id)), 0) + 1;
}

function createBuiltinRates(defaultRateCents) {
    return [
        { id: nextRateId(), rate_code: "ST", rate_cents: defaultRateCents, is_builtin: true, sort_order: 1 },
        { id: nextRateId() + 1, rate_code: "OT", rate_cents: Math.round(defaultRateCents * 1.5), is_builtin: true, sort_order: 2 },
        { id: nextRateId() + 2, rate_code: "TT", rate_cents: Math.round(defaultRateCents * 0.5), is_builtin: true, sort_order: 3 }
    ];
}

function emptyProjectDraft(overrides = {}) {
    return {
        id: "",
        project_number: "",
        customer_id: projectState.customers[0]?.id || "",
        customer_name: projectState.customers[0]?.customer_name || "",
        description: "",
        default_rate_cents: 12500,
        rates: [
            { id: 0, rate_code: "ST", rate_cents: 12500, is_builtin: true, sort_order: 1 },
            { id: 0, rate_code: "OT", rate_cents: 18750, is_builtin: true, sort_order: 2 },
            { id: 0, rate_code: "TT", rate_cents: 6250, is_builtin: true, sort_order: 3 }
        ],
        spent_to_date_cents: 0,
        updated_at: new Date().toISOString(),
        ...overrides
    };
}

function filteredProjects() {
    const query = projectState.searchQuery.trim().toLowerCase();

    return projectState.projects.filter((project) => {
        const matchesCustomer = projectState.customerFilter === "all" || String(project.customer_id) === projectState.customerFilter;
        const haystack = [
            project.project_number,
            project.customer_name,
            project.description,
            ...project.rates.map((rate) => rate.rate_code)
        ].join(" ").toLowerCase();
        const matchesQuery = !query || haystack.includes(query);

        return matchesCustomer && matchesQuery;
    });
}

function selectedProject() {
    return projectState.projects.find((project) => project.id === projectState.selectedId) || null;
}

function renderCustomerFilterOptions() {
    const select = document.getElementById("project-customer-filter");
    const editorSelect = document.getElementById("project-customer");
    if (!select || !editorSelect) {
        return;
    }

    const options = [
        '<option value="all">All Customers</option>',
        ...projectState.customers.map((customer) => `<option value="${customer.id}">${customer.customer_name}</option>`)
    ].join("");
    select.innerHTML = options;
    select.value = projectState.customerFilter;

    editorSelect.innerHTML = projectState.customers.map((customer) => `<option value="${customer.id}">${customer.customer_name}</option>`).join("");
}

function renderMetrics(projects) {
    if (projectState.isLoading) {
        setText("projects-mode", "Loading...");
        setText("metric-visible-projects", "-");
        setText("metric-linked-customers", "-");
        setText("metric-default-rate", "-");
        setText("metric-custom-rates", "-");
        return;
    }

    const linkedCustomers = new Set(projects.map((project) => project.customer_id)).size;
    const averageRate = projects.length === 0
        ? 0
        : Math.round(projects.reduce((sum, project) => sum + project.default_rate_cents, 0) / projects.length);
    const customRates = projects.reduce((sum, project) => sum + project.rates.filter((rate) => !rate.is_builtin).length, 0);

    setText("projects-mode", window.location.protocol === "file:" ? "File Mode" : "SQLite Mode");
    setText("metric-visible-projects", String(projects.length));
    setText("metric-linked-customers", String(linkedCustomers));
    setText("metric-default-rate", money(averageRate));
    setText("metric-custom-rates", String(customRates));
}

function rateSummary(project) {
    return project.rates.map((rate) => `${rate.rate_code}: ${money(rate.rate_cents)}`).join(" · ");
}

function renderProjectRows(projects) {
    const tbody = document.getElementById("projects-table-body");
    const emptyState = document.getElementById("projects-empty-state");
    if (!tbody || !emptyState) {
        return;
    }

    if (projectState.isLoading) {
        tbody.innerHTML = "";
        setEmptyState("Loading projects...", "The projects screen is waiting for its bootstrap payload from the API.");
        emptyState.classList.remove("hidden");
        return;
    }

    if (projectState.loadError) {
        tbody.innerHTML = "";
        setEmptyState("Project load failed", projectState.loadError);
        emptyState.classList.remove("hidden");
        return;
    }

    if (projects.length === 0) {
        tbody.innerHTML = "";
        setEmptyState("No projects match the current filter.", "Adjust the search, switch the customer filter, or create a new project draft.");
        emptyState.classList.remove("hidden");
        return;
    }

    emptyState.classList.add("hidden");
    tbody.innerHTML = projects.map((project) => {
        const isSelected = project.id === projectState.selectedId;

        return `
            <tr class="cursor-pointer border-t border-line/70 ${isSelected ? "bg-brand/5" : "bg-white/30 hover:bg-white/60"}" data-project-select="${project.id}">
                <td class="px-4 py-4 align-top">
                    <div class="font-mono text-sm font-semibold text-ink">${project.project_number}</div>
                    <div class="mt-1 text-xs text-muted">${project.description}</div>
                </td>
                <td class="px-4 py-4 align-top text-sm text-ink">${project.customer_name}</td>
                <td class="px-4 py-4 align-top text-xs leading-6 text-muted">${rateSummary(project)}</td>
                <td class="px-4 py-4 align-top text-right font-mono text-sm text-ink">${money(project.default_rate_cents)}</td>
            </tr>
        `;
    }).join("");

    tbody.querySelectorAll("[data-project-select]").forEach((row) => {
        row.addEventListener("click", () => {
            projectState.selectedId = Number(row.dataset.projectSelect);
            projectState.draftProject = null;
            render();
        });
    });
}

function renderBuiltinRatePreview(defaultRateCents) {
    const preview = document.getElementById("builtin-rate-preview");
    if (!preview) {
        return;
    }

    const builtins = [
        { code: "ST", cents: defaultRateCents },
        { code: "OT", cents: Math.round(defaultRateCents * 1.5) },
        { code: "TT", cents: Math.round(defaultRateCents * 0.5) }
    ];

    preview.innerHTML = builtins.map((rate) => `
        <div class="flex items-center justify-between rounded-2xl border border-line bg-white/70 px-4 py-3 text-sm">
            <div>
                <p class="font-mono font-semibold text-ink">${rate.code}</p>
                <p class="text-xs text-muted">Built-in derived rate</p>
            </div>
            <p class="font-mono text-ink">${money(rate.cents)}</p>
        </div>
    `).join("");
}

function renderCustomRateInputs(customRates) {
    const list = document.getElementById("custom-rates-list");
    if (!list) {
        return;
    }

    if (customRates.length === 0) {
        list.innerHTML = '<div class="rounded-2xl border border-dashed border-line bg-white/40 px-4 py-4 text-sm text-muted">No custom rates yet. Add one when the project needs a special billing code.</div>';
        return;
    }

    list.innerHTML = customRates.map((rate, index) => `
        <div class="grid gap-3 rounded-[1.1rem] border border-line bg-white/70 p-4 md:grid-cols-[8rem_minmax(10rem,1fr)]" data-custom-rate-index="${index}">
            <div>
                <label class="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">Code</label>
                <input class="mt-2 w-full rounded-xl border border-line bg-white px-3 py-2 text-sm text-ink outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20" data-field="rate_code" type="text" value="${escapeHtml(rate.rate_code)}">
            </div>
            <div>
                <label class="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">Rate</label>
                <input class="mt-2 w-full rounded-xl border border-line bg-white px-3 py-2 text-sm text-ink outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20" data-field="rate_dollars" min="0" step="0.01" type="number" value="${(rate.rate_cents / 100).toFixed(2)}">
            </div>
            <button class="inline-flex items-center justify-center rounded-full border border-danger/20 bg-danger/10 px-4 py-2 text-sm font-semibold text-danger transition hover:bg-danger/15 md:col-span-2 md:justify-self-start" data-remove-custom-rate="${index}" type="button">Remove</button>
        </div>
    `).join("");

    list.querySelectorAll("[data-remove-custom-rate]").forEach((button) => {
        button.addEventListener("click", () => {
            const index = Number(button.dataset.removeCustomRate);
            const source = projectState.draftProject || selectedProject();
            if (!source) {
                return;
            }
            const customRatesOnly = source.rates.filter((rate) => !rate.is_builtin);
            customRatesOnly.splice(index, 1);
            updateEditorRates(customRatesOnly);
        });
    });

    list.querySelectorAll("[data-custom-rate-index]").forEach((row) => {
        row.querySelectorAll("input").forEach((input) => {
            input.addEventListener("input", () => {
                const index = Number(row.dataset.customRateIndex);
                const field = input.dataset.field;
                const source = projectState.draftProject || selectedProject();
                if (!source) {
                    return;
                }
                const customRatesOnly = source.rates.filter((rate) => !rate.is_builtin).map((rate) => ({ ...rate }));
                const target = customRatesOnly[index];
                if (!target) {
                    return;
                }
                if (field === "rate_code") {
                    target.rate_code = input.value.toUpperCase();
                    input.value = target.rate_code;
                } else if (field === "rate_dollars") {
                    target.rate_cents = Math.round(Number(input.value || 0) * 100);
                }
                updateEditorRates(customRatesOnly, { render: false });
            });
        });
    });
}

function updateEditorRates(customRatesOnly, options = {}) {
    const source = projectState.draftProject || selectedProject() || emptyProjectDraft();
    const defaultRateCents = readDefaultRateInput();
    const customer = projectState.customers.find((item) => item.id === Number(document.getElementById("project-customer")?.value || source.customer_id));
    projectState.draftProject = {
        ...source,
        customer_id: customer?.id || source.customer_id,
        customer_name: customer?.customer_name || source.customer_name,
        default_rate_cents: defaultRateCents,
        rates: [
            ...createBuiltinRates(defaultRateCents),
            ...customRatesOnly.map((rate, index) => ({
                id: rate.id || nextRateId() + index,
                rate_code: rate.rate_code,
                rate_cents: rate.rate_cents,
                is_builtin: false,
                sort_order: rate.sort_order
            }))
        ]
    };
    if (options.render !== false) {
        renderEditor(projectState.draftProject);
    }
}

function readDefaultRateInput() {
    return Math.round(Number(document.getElementById("project-default-rate")?.value || 0) * 100);
}

function renderEditor(project) {
    const form = document.getElementById("project-form");
    if (!form) {
        return;
    }

    const current = project || emptyProjectDraft();

    document.getElementById("project-id").value = current.id;
    document.getElementById("project-number").value = current.project_number;
    document.getElementById("project-customer").value = String(current.customer_id || "");
    document.getElementById("project-description").value = current.description;
    document.getElementById("project-default-rate").value = (current.default_rate_cents / 100).toFixed(2);

    setText("project-editor-title", current.project_number ? `Project ${current.project_number}` : "New Project Draft");
    setText("project-detail-customer", current.customer_name || "None selected");
    setText("project-detail-rate-count", String(current.rates.length));
    setText("project-detail-default-rate", money(current.default_rate_cents));

    const statusChip = document.getElementById("project-editor-status-chip");
    if (statusChip) {
        statusChip.className = "rounded-full border border-line bg-panel/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-ink";
        statusChip.textContent = current.project_number ? "Project" : "Draft";
    }

    renderBuiltinRatePreview(current.default_rate_cents);
    renderCustomRateInputs(current.rates.filter((rate) => !rate.is_builtin));
}

function render() {
    renderNavState();
    renderCustomerFilterOptions();

    const projects = filteredProjects();
    renderMetrics(projects);
    renderProjectRows(projects);

    const project = selectedProject() || projectState.draftProject;
    renderEditor(project);
}

async function saveProject(event) {
    event.preventDefault();

    if (projectState.isSaving) {
        return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    const projectId = Number(document.getElementById("project-id")?.value || 0);
    const existing = projectState.projects.find((project) => project.id === projectId);
    const customRates = (projectState.draftProject || existing || emptyProjectDraft()).rates.filter((rate) => !rate.is_builtin);
    const defaultRateCents = Math.round(Number(formData.get("default_rate_dollars") || 0) * 100);

    const payload = {
        project_number: String(formData.get("project_number") || "").trim(),
        customer_id: Number(formData.get("customer_id") || 0),
        description: String(formData.get("description") || "").trim(),
        default_rate_cents: defaultRateCents,
        rates: [
            ...createBuiltinRates(defaultRateCents),
            ...customRates.map((rate) => ({
                rate_code: rate.rate_code,
                rate_cents: rate.rate_cents,
                is_builtin: false,
                sort_order: rate.sort_order
            }))
        ]
    };

    const method = projectId ? "PUT" : "POST";
    const path = projectId ? `/${projectId}` : "";

    try {
        projectState.isSaving = true;
        const response = await fetch(projectsUrl(path), {
            method,
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });
        const responseBody = await response.json();

        if (!response.ok) {
            throw new Error(extractErrorMessage(responseBody, "Unable to save project."));
        }

        const project = responseBody?.data?.project;
        if (!project) {
            throw new Error("Project save completed without a returned record.");
        }

        upsertProject({
            ...project,
            rates: Array.isArray(project.rates) ? project.rates.map((rate) => ({ ...rate })) : []
        });
        projectState.selectedId = project.id;
        projectState.draftProject = null;
    } catch (error) {
        window.alert(error instanceof Error ? error.message : "Unable to save project.");
    } finally {
        projectState.isSaving = false;
    }

    render();
}

function clearProjectDraft(copyCurrent = false) {
    if (copyCurrent && selectedProject()) {
        const original = selectedProject();
        projectState.selectedId = null;
        projectState.draftProject = emptyProjectDraft({
            project_number: `${original.project_number}-COPY`,
            customer_id: original.customer_id,
            customer_name: original.customer_name,
            description: original.description,
            default_rate_cents: original.default_rate_cents,
            rates: original.rates.map((rate) => ({ ...rate, id: 0 })),
            spent_to_date_cents: 0
        });
        render();
        return;
    }

    projectState.selectedId = null;
    projectState.draftProject = emptyProjectDraft();
    render();
}

function bindEvents() {
    document.getElementById("project-search")?.addEventListener("input", (event) => {
        projectState.searchQuery = event.target.value;
        render();
    });

    document.getElementById("project-customer-filter")?.addEventListener("change", (event) => {
        projectState.customerFilter = event.target.value;
        render();
    });

    document.getElementById("project-form")?.addEventListener("submit", saveProject);
    document.getElementById("new-project-button")?.addEventListener("click", () => clearProjectDraft(false));
    document.getElementById("clear-project-form-button")?.addEventListener("click", () => clearProjectDraft(false));
    document.getElementById("duplicate-project-button")?.addEventListener("click", () => clearProjectDraft(true));
    document.getElementById("reset-project-filters-button")?.addEventListener("click", () => {
        projectState.searchQuery = "";
        projectState.customerFilter = "all";
        const search = document.getElementById("project-search");
        if (search) {
            search.value = "";
        }
        render();
    });

    document.getElementById("project-customer")?.addEventListener("change", () => {
        const source = projectState.draftProject || selectedProject() || emptyProjectDraft();
        const customer = projectState.customers.find((item) => item.id === Number(document.getElementById("project-customer")?.value || source.customer_id));
        projectState.draftProject = {
            ...source,
            customer_id: customer?.id || source.customer_id,
            customer_name: customer?.customer_name || source.customer_name
        };
        renderEditor(projectState.draftProject);
    });

    document.getElementById("project-default-rate")?.addEventListener("input", () => {
        const source = projectState.draftProject || selectedProject() || emptyProjectDraft();
        const customRates = source.rates.filter((rate) => !rate.is_builtin).map((rate) => ({ ...rate }));
        updateEditorRates(customRates);
    });

    document.getElementById("add-custom-rate-button")?.addEventListener("click", () => {
        const source = projectState.draftProject || selectedProject() || emptyProjectDraft();
        const customRates = source.rates.filter((rate) => !rate.is_builtin).map((rate) => ({ ...rate }));
        customRates.push({ id: 0, rate_code: `C${customRates.length + 1}`, rate_cents: readDefaultRateInput(), is_builtin: false, sort_order: 10 + customRates.length });
        updateEditorRates(customRates);
    });
}

window.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    render();
    void loadProjects();
});
