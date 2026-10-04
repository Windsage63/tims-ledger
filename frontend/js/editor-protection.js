/**
 * @fileoverview Protect saved records and warn before discarding browser drafts.
 * @license Apache-2.0
 * @copyright 2026 Timothy Mallory
 */

function cloneEditorData(value) {
    return value == null ? value : JSON.parse(JSON.stringify(value));
}

// Read controls directly, including disabled fields (FormData omits them).
function editorFormSnapshot(formId) {
    const fields = [...(document.getElementById(formId)?.querySelectorAll("input, select, textarea") || [])];
    return fields.filter((field) => field.type !== "hidden").map((field) => [
        field.id || field.name || field.dataset.field,
        field.type === "checkbox" ? field.checked
            : field.type === "number" ? (field.value === "" ? "" : Number(field.value))
                : field.value.trim()
    ]);
}

const editorProtection = (() => {
    let adapter = null;
    let mode = false;
    let baseline = null;
    let baselineData = null;
    let duplicate = false;
    let unloadInstalled = false;
    let departing = false;

    const busy = () => Boolean(adapter?.busy());
    const locked = () => Boolean(adapter?.recordId()) && !mode;
    const dirty = () => Boolean(adapter && baseline !== null &&
        (duplicate || JSON.stringify(adapter.snapshot()) !== baseline));
    const beforeUnload = (event) => {
        if (!departing && (dirty() || busy())) {
            event.preventDefault();
            event.returnValue = "";
        }
    };

    function updateUnload() {
        const needed = !departing && (dirty() || busy());
        if (needed === unloadInstalled) return;
        window[needed ? "addEventListener" : "removeEventListener"]("beforeunload", beforeUnload);
        unloadInstalled = needed;
    }

    function accept(options = {}) {
        if (!adapter) return;
        const id = adapter.recordId() || null;
        baseline = JSON.stringify(adapter.snapshot());
        baselineData = cloneEditorData(adapter.capture());
        duplicate = Boolean(options.duplicate);
        if (options.lock || !id) mode = false;
        departing = false;
        refresh();
    }

    function refresh() {
        if (!adapter) return;
        const id = adapter.recordId() || null;
        if (!busy() && baseline === null) {
            accept();
            return;
        }
        const toggle = document.getElementById("edit-mode-button");
        if (toggle) {
            toggle.classList.toggle("edit-mode-active", mode);
            toggle.setAttribute("aria-pressed", String(mode));
            toggle.disabled = busy() || !id;
            toggle.title = !id ? "New records are already editable." : mode
                ? "Editing enabled. Turn off to protect this record."
                : "Existing record protected. Enable Edit Mode to make changes.";
        }
        const blocked = locked() || busy();
        document.querySelectorAll(`#${adapter.formId} input:not([type=hidden]), #${adapter.formId} select, #${adapter.formId} textarea, #${adapter.formId} button[type=submit], ${adapter.mutationControls || ".unused-mutation-control"}`)
            .forEach((control) => { control.disabled = blocked; });
        adapter.applyProtection?.(blocked);
        updateUnload();
    }

    function allowTransition() {
        if (busy()) return false;
        return !dirty() || window.confirm("You have unsaved changes. Continue and lose those changes?");
    }

    function toggle() {
        if (!adapter || busy() || !adapter.recordId()) return;
        if (mode && dirty()) {
            if (!allowTransition()) return;
            adapter.restore(cloneEditorData(baselineData));
            duplicate = false;
        }
        mode = !mode;
        adapter.render();
        refresh();
    }

    function register(config) {
        adapter = config;
        refresh();
    }

    document.addEventListener("input", updateUnload);
    document.addEventListener("change", updateUnload);
    // Capture synthetic/keyboard submissions before the screen's handlers too.
    ["input", "change", "submit"].forEach((type) => {
        document.addEventListener(type, (event) => {
            const owned = adapter && (event.target.closest(`#${adapter.formId}`) ||
                (adapter.mutationControls && event.target.matches(adapter.mutationControls)));
            if (!owned || (!locked() && !busy())) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            adapter.render();
        }, true);
    });
    document.addEventListener("click", (event) => {
        const link = event.target.closest("a[href]");
        if (!adapter || !link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.target === "_blank" || link.hasAttribute("download")) return;
        const url = new URL(link.href, window.location.href);
        if (url.origin === window.location.origin && url.pathname === window.location.pathname && url.search === window.location.search) return;
        if (!allowTransition()) {
            event.preventDefault();
            event.stopImmediatePropagation();
            return;
        }
        departing = true;
        updateUnload();
        // Recover unload protection if another listener canceled navigation.
        window.setTimeout(() => { departing = false; updateUnload(); }, 1000);
    }, true);
    window.addEventListener("pageshow", () => {
        mode = false;
        departing = false;
        if (adapter) adapter.render();
        refresh();
    });
    window.addEventListener("DOMContentLoaded", () => {
        document.getElementById("edit-mode-button")?.addEventListener("click", toggle);
    });

    return {
        register, refresh, accept, allowTransition, dirty, locked,
        canWrite: () => Boolean(adapter && !locked()),
        saved: () => accept({ lock: true }),
        enableRetry: () => { mode = Boolean(adapter?.recordId()); refresh(); }
    };
})();
