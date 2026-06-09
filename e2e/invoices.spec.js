const fs = require("fs/promises");
const path = require("path");
const { test, expect } = require("@playwright/test");


test("issued invoice page supports checkbox edits, save, and stored HTML print", async ({ page }) => {
    await page.goto("/static/invoices.html");

    await page.locator('[data-invoice-select="201"]').click();
    await expect(page.locator("#invoice-number")).toHaveValue("INV-2026-014");

    const selectedTimeCheckbox = page.locator('#eligible-time-list input[data-selection-id="403"]');
    const availableTimeCheckbox = page.locator('#eligible-time-list input[data-selection-id="407"]');
    const availableExpenseCheckbox = page.locator('#eligible-expenses-list input[data-selection-id="815"]');

    await expect(selectedTimeCheckbox).toBeChecked();
    await expect(availableTimeCheckbox).not.toBeChecked();
    await expect(availableExpenseCheckbox).not.toBeChecked();

    await selectedTimeCheckbox.uncheck();
    await expect(selectedTimeCheckbox).not.toBeChecked();
    await expect(page.locator("#invoice-summary-time")).toHaveText("$0.00");

    await selectedTimeCheckbox.check();
    await expect(selectedTimeCheckbox).toBeChecked();
    await expect(page.locator("#invoice-summary-time")).toHaveText("$672.75");

    await availableExpenseCheckbox.check();
    await expect(availableExpenseCheckbox).toBeChecked();
    await expect(page.locator("#invoice-summary-expense")).toHaveText("$185.00");

    await page.locator("#invoice-po-number").fill("PO-BROWSER-SMOKE");
    await page.locator("#save-invoice-button").click();
    await expect(page.locator("#save-invoice-button")).toHaveText("Save Invoice");

    await page.locator('[data-invoice-select="301"]').click();
    await expect(page.locator("#invoice-number")).toHaveValue("INV-2026-023");
    await page.locator('[data-invoice-select="201"]').click();
    await expect(page.locator("#invoice-po-number")).toHaveValue("PO-BROWSER-SMOKE");
    await expect(page.locator('#eligible-expenses-list input[data-selection-id="815"]')).toBeChecked();

    const popupPromise = page.waitForEvent("popup");
    await page.locator("#print-invoice-button").click();
    const popup = await popupPromise;
    await popup.waitForLoadState("domcontentloaded");
    await expect(popup).toHaveTitle(/Invoice INV-2026-014/);
    await expect(popup.locator("body")).toContainText("PO-BROWSER-SMOKE");

    const invoiceFile = path.join(process.env.WINDS_LEDGER_E2E_DATA_DIR, "invoices", "INV-2026-014.html");
    await expect.poll(async () => {
        try {
            await fs.access(invoiceFile);
            return true;
        } catch {
            return false;
        }
    }).toBe(true);

    await expect.poll(async () => fs.readFile(invoiceFile, "utf-8")).toContain("PO-BROWSER-SMOKE");
    await expect.poll(async () => fs.readFile(invoiceFile, "utf-8")).toContain("Subdivision review filing fee.");

    await popup.close();
});