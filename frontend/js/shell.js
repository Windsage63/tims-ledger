/**
 * @fileoverview Control shared menus, backup status, and backup notifications.
 * @license Apache-2.0
 * @copyright 2026 Timothy Mallory
 */

const shellBackups = { backups: [], busy: false, cooldownUntil: 0, error: "" };

function backupTimestamp(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value || "") : date.toLocaleString();
}

function renderShellBackups() {
    const button = document.getElementById("shell-backup-button");
    button.disabled = shellBackups.busy || Date.now() < shellBackups.cooldownUntil;
    button.textContent = shellBackups.busy ? "Working…" : "Back up";
    setText("last-backup", shellBackups.error || (shellBackups.backups[0]
        ? `Last backup: ${backupTimestamp(shellBackups.backups[0].created_at)}` : "No backups yet"));
    window.dispatchEvent(new CustomEvent("backups:changed", { detail: shellBackups }));
}

async function refreshShellBackups() {
    try {
        const data = await apiRequestJson("/api/backups", "", {}, "Unable to load backups.");
        shellBackups.backups = data.backups || [];
        shellBackups.error = "";
    } catch (error) {
        shellBackups.error = error.message;
    }
    renderShellBackups();
}

async function createShellBackup() {
    if (shellBackups.busy || Date.now() < shellBackups.cooldownUntil) return;
    shellBackups.busy = true;
    renderShellBackups();
    try {
        const data = await apiRequestJson("/api/backups", "", { method: "POST" }, "Unable to create backup.");
        shellBackups.backups = data.backups || [];
        shellBackups.error = "";
        showToast(data.backup ? `Created ${data.backup.file_name}.` : "Backup created.", "success");
    } catch (error) {
        showToast(error.message);
    } finally {
        shellBackups.busy = false;
        shellBackups.cooldownUntil = Date.now() + 5000;
        renderShellBackups();
        window.setTimeout(renderShellBackups, 5000);
    }
}

window.addEventListener("DOMContentLoaded", () => {
    const menus = [...document.querySelectorAll(".shell-menu")];
    document.addEventListener("click", (event) => {
        menus.forEach((menu) => { if (!menu.contains(event.target)) menu.open = false; });
    });
    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        const openMenu = menus.find((menu) => menu.open);
        menus.forEach((menu) => { menu.open = false; });
        openMenu?.querySelector("summary")?.focus();
    });
    menus.forEach((menu) => menu.addEventListener("toggle", () => {
        if (menu.open) menus.forEach((other) => { if (other !== menu) other.open = false; });
    }));
    document.getElementById("shell-backup-button").addEventListener("click", () => void createShellBackup());
    void refreshShellBackups();
});
