const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const root = path.resolve(__dirname, "..");

function makeClassList() {
    return {
        values: new Set(),
        toggle(className, force) {
            if (force) {
                this.values.add(className);
            } else {
                this.values.delete(className);
            }
        },
        add(className) {
            this.values.add(className);
        },
        remove(className) {
            this.values.delete(className);
        },
        contains(className) {
            return this.values.has(className);
        }
    };
}

function makeElement(attributes = {}) {
    return {
        attributes,
        classList: makeClassList(),
        dataset: {},
        disabled: false,
        href: attributes.href || "",
        innerHTML: "",
        textContent: "",
        value: "",
        addEventListener() {},
        closest() {
            return null;
        },
        getAttribute(name) {
            return this.attributes[name] || "";
        },
        querySelector() {
            return null;
        },
        querySelectorAll() {
            return [];
        }
    };
}

function makeDocument({ elements = {}, navLinks = [] } = {}) {
    return {
        elements,
        getElementById(id) {
            return this.elements[id] || null;
        },
        querySelectorAll(selector) {
            if (selector === ".side-nav .nav-link") {
                return navLinks;
            }
            return [];
        }
    };
}

function loadScript(fileName, options = {}) {
    const code = fs.readFileSync(path.join(root, "frontend", "js", fileName), "utf8");
    const utilsCode = fileName === "utils.js"
        ? ""
        : fs.readFileSync(path.join(root, "frontend", "js", "utils.js"), "utf8");
    const document = options.document || makeDocument();
    const window = {
        location: {
            hash: options.hash || "",
            pathname: options.pathname || `/static/${fileName.replace(".js", ".html")}`,
            protocol: options.protocol || "http:"
        },
        addEventListener() {},
        alert() {},
        confirm: () => true,
        setTimeout,
        clearTimeout,
        AbortController: global.AbortController,
        open: () => ({ close() {}, location: { replace() {} } })
    };
    const sandbox = {
        console,
        document,
        fetch: options.fetch || (async () => {
            throw new Error("Unexpected fetch call");
        }),
        FormData: global.FormData,
        Intl,
        JSON,
        Math,
        Number,
        Set,
        String,
        URLSearchParams,
        window
    };
    sandbox.globalThis = sandbox;
    vm.createContext(sandbox);
    if (utilsCode) {
        vm.runInContext(utilsCode, sandbox, { filename: "utils.js" });
    }
    vm.runInContext(code, sandbox, { filename: fileName });
    return sandbox;
}

const currencyFiles = ["app.js", "expenses.js", "invoices.js", "payments.js", "time.js"];
const setTextFiles = ["app.js", "customers.js", "expenses.js", "invoices.js", "payments.js", "projects.js", "time.js"];
const compactErrorFiles = ["customers.js", "projects.js", "time.js"];
const richErrorFiles = ["expenses.js", "invoices.js", "payments.js"];
const navFiles = ["customers.js", "expenses.js", "invoices.js", "payments.js", "projects.js", "time.js"];

test("currency helpers format cents as USD", () => {
    for (const fileName of currencyFiles) {
        const context = loadScript(fileName);
        assert.equal(context.currency(123456), "$1,234.56", `${fileName} formats positive cents`);
        assert.equal(context.currency(0), "$0.00", `${fileName} formats zero`);
        assert.equal(context.currency(null), "$0.00", `${fileName} treats null as zero`);
        assert.equal(context.currency(-425), "-$4.25", `${fileName} formats negative cents`);
    }
});

test("money aliases format cents as USD", () => {
    const customers = loadScript("customers.js");
    assert.equal(customers.formatCurrency(12500), "$125.00");

    const projects = loadScript("projects.js");
    assert.equal(projects.money(18750), "$187.50");
});

test("setText updates existing elements and ignores missing elements", () => {
    for (const fileName of setTextFiles) {
        const target = makeElement();
        const context = loadScript(fileName, {
            document: makeDocument({ elements: { target } })
        });
        assert.doesNotThrow(() => context.setText("missing", "ignored"), `${fileName} tolerates missing element`);
        context.setText("target", "Updated");
        assert.equal(target.textContent, "Updated", `${fileName} writes textContent`);
    }
});

test("escapeHtml escapes user-controlled markup characters", () => {
    for (const fileName of ["app.js", "invoices.js"]) {
        const context = loadScript(fileName);
        assert.equal(
            context.escapeHtml(`A&B <tag attr="quote">'single'</tag>`),
            "A&amp;B &lt;tag attr=&quot;quote&quot;&gt;&#039;single&#039;&lt;/tag&gt;",
            `${fileName} escapes HTML-sensitive characters`
        );
        assert.equal(context.escapeHtml(null), "", `${fileName} treats nullish values as empty`);
    }
});

test("compact extractErrorMessage helpers prefer validation messages, detail, then fallback", () => {
    for (const fileName of compactErrorFiles) {
        const context = loadScript(fileName);
        assert.equal(context.extractErrorMessage({ errors: [{ message: "First error" }] }, "Fallback"), "First error");
        assert.equal(context.extractErrorMessage({ detail: "Detail error" }, "Fallback"), "Detail error");
        assert.equal(context.extractErrorMessage({ detail: [{ msg: "Validation error" }] }, "Fallback"), "Validation error");
        assert.equal(context.extractErrorMessage({}, "Fallback"), "Fallback");
        assert.equal(context.extractErrorMessage(null, "Fallback"), "Fallback");
    }
});

test("rich extractErrorMessage helpers handle strings, arrays, Error-like objects, and fallback", () => {
    for (const fileName of richErrorFiles) {
        const context = loadScript(fileName);
        assert.equal(context.extractErrorMessage("String error", "Fallback"), "String error");
        assert.equal(context.extractErrorMessage({ detail: "Detail error" }, "Fallback"), "Detail error");
        assert.equal(
            context.extractErrorMessage({ detail: [{ msg: "First" }, { message: "Second" }, "Third"] }, "Fallback"),
            "First Second Third"
        );
        assert.equal(
            context.extractErrorMessage({ detail: [{ loc: ["body", "reference_number"], msg: "Value error, This field is required." }] }, "Fallback"),
            "Reference No.: This field is required."
        );
        assert.equal(context.extractErrorMessage({ message: "Message error" }, "Fallback"), "Message error");
        assert.equal(context.extractErrorMessage(null, "Fallback"), "Fallback");
    }
});

test("dollar input helpers convert cents and decimal input consistently", () => {
    for (const fileName of ["expenses.js", "payments.js"]) {
        const context = loadScript(fileName);
        assert.equal(context.dollarsInput(12345), "123.45", `${fileName} formats cents for inputs`);
        assert.equal(context.dollarsInput(null), "0.00", `${fileName} treats null cents as zero`);
        assert.equal(context.centsFromInput("123.456"), 12346, `${fileName} rounds fractional cents`);
        assert.equal(context.centsFromInput(""), 0, `${fileName} treats blank input as zero`);
        assert.equal(context.centsFromInput("-4.25"), -425, `${fileName} preserves negative input`);
    }
});

test("renderNavState marks only the current page link active", () => {
    for (const fileName of navFiles) {
        const pageName = fileName.replace(".js", ".html");
        const activeLink = makeElement({ href: `./${pageName}` });
        const inactiveLink = makeElement({ href: "./index.html" });
        const externalLink = makeElement({ href: "#overview" });
        const context = loadScript(fileName, {
            pathname: `/static/${pageName}`,
            document: makeDocument({ navLinks: [activeLink, inactiveLink, externalLink] })
        });

        context.renderNavState();

        assert.equal(activeLink.classList.contains("bg-gradient-to-r"), true, `${fileName} activates current page`);
        assert.equal(activeLink.classList.contains("text-white"), true, `${fileName} applies active text style`);
        assert.equal(activeLink.classList.contains("bg-white/10"), false, `${fileName} removes inactive background`);
        assert.equal(inactiveLink.classList.contains("bg-gradient-to-r"), false, `${fileName} does not activate other pages`);
        assert.equal(inactiveLink.classList.contains("bg-white/10"), true, `${fileName} keeps other pages inactive`);
        assert.equal(externalLink.classList.contains("bg-gradient-to-r"), false, `${fileName} ignores hash links`);
    }
});

test("requestJson helpers call screen API roots, merge headers, and return envelope data", async () => {
    const calls = [];
    const fetch = async (url, options) => {
        calls.push({ url, options });
        return {
            ok: true,
            async json() {
                return { data: { ok: true } };
            }
        };
    };

    const invoices = loadScript("invoices.js", { fetch });
    assert.deepEqual(await invoices.requestJson("/bootstrap", { headers: { "X-Test": "yes" } }), { ok: true });
    assert.equal(calls[0].url, "/api/invoices/bootstrap");
    assert.equal(calls[0].options.headers.Accept, "application/json");
    assert.equal(calls[0].options.headers["X-Test"], "yes");

    const payments = loadScript("payments.js", { fetch });
    assert.deepEqual(await payments.requestJson("/bootstrap"), { ok: true });
    assert.equal(calls[1].url, "/api/payments/bootstrap");
    assert.equal(calls[1].options.headers.Accept, "application/json");
});

test("requestJson helpers throw extracted messages for non-ok responses", async () => {
    const fetch = async () => ({
        ok: false,
        async json() {
            return { detail: [{ msg: "Bad request" }] };
        }
    });

    const invoices = loadScript("invoices.js", { fetch });
    await assert.rejects(
        () => invoices.requestJson("/bad", {}, "Fallback"),
        /Bad request/
    );

    const payments = loadScript("payments.js", { fetch });
    await assert.rejects(
        () => payments.requestJson("/bad", {}, "Fallback"),
        /Bad request/
    );
});

test("payment save validation failures alert without replacing the ledger error state", async () => {
    const alerts = [];
    const elements = {
        "payment-customer": makeElement(),
        "payment-date": makeElement(),
        "payment-reference": makeElement(),
        "payment-amount": makeElement(),
        "payment-notes": makeElement()
    };
    elements["payment-customer"].value = "0";
    elements["payment-date"].value = "2026-05-31";
    elements["payment-reference"].value = "";
    elements["payment-amount"].value = "0";
    const context = loadScript("payments.js", {
        document: makeDocument({ elements }),
        fetch: async () => {
            return {
                ok: false,
                async json() {
                    return { detail: [{ loc: ["body", "customer_id"], msg: "Value error, Customer is required." }] };
                }
            };
        }
    });
    context.window.alert = (message) => {
        alerts.push(message);
    };
    vm.runInContext(`
        paymentsState.editor.payment = {
            id: null,
            customer_id: 0,
            customer_name: "Customer",
            payment_date: "2026-05-31",
            reference_number: "",
            amount_cents: 0,
            applied_amount_cents: 0,
            unapplied_amount_cents: 0,
            application_status: "unapplied",
            notes: ""
        };
        paymentsState.loadError = "";
    `, context);

    await context.savePayment();

    assert.deepEqual(alerts, ["Customer: Customer is required."]);
    assert.equal(vm.runInContext("paymentsState.loadError", context), "");
});

test("payment table renderer alerts load errors without clearing existing rows", () => {
    const alerts = [];
    const tbody = makeElement();
    const emptyState = makeElement();
    const heading = makeElement();
    const detail = makeElement();
    tbody.innerHTML = "<tr><td>Existing payment</td></tr>";
    emptyState.querySelector = (selector) => {
        if (selector === "p.font-display") {
            return heading;
        }
        if (selector === "p.mt-2") {
            return detail;
        }
        return null;
    };
    const context = loadScript("payments.js", {
        document: makeDocument({
            elements: {
                "payment-table-body": tbody,
                "payment-empty-state": emptyState
            }
        })
    });
    context.window.alert = (message) => {
        alerts.push(message);
    };
    vm.runInContext(`
        paymentsState.isLoading = false;
        paymentsState.loadError = "Value error, This field is required.";
    `, context);

    context.renderPaymentRows([
        {
            id: 1,
            payment_date: "2026-05-31",
            customer_name: "Customer",
            reference_number: "REF",
            amount_cents: 100,
            unapplied_amount_cents: 100,
            application_status: "unapplied"
        }
    ]);

    assert.deepEqual(alerts, ["Value error, This field is required."]);
    assert.match(tbody.innerHTML, /REF/);
    assert.equal(vm.runInContext("paymentsState.loadError", context), "");
    assert.equal(emptyState.classList.contains("hidden"), true);
});

test("requestBackupJson uses raw backup paths and returns envelope data", async () => {
    const calls = [];
    const fetch = async (url, options) => {
        calls.push({ url, options });
        return {
            ok: true,
            async json() {
                return { data: { backups: ["one"] } };
            }
        };
    };
    const context = loadScript("app.js", { fetch });

    assert.deepEqual(await context.requestBackupJson("/api/backups", { method: "POST" }), { backups: ["one"] });
    assert.equal(calls[0].url, "/api/backups");
    assert.equal(calls[0].options.method, "POST");
    assert.equal(calls[0].options.headers.Accept, "application/json");
});

test("requestBackupJson throws detail, message, or default backup errors", async () => {
    const detailContext = loadScript("app.js", {
        fetch: async () => ({
            ok: false,
            async json() {
                return { detail: "Restore failed" };
            }
        })
    });
    await assert.rejects(() => detailContext.requestBackupJson("/api/backups"), /Restore failed/);

    const defaultContext = loadScript("app.js", {
        fetch: async () => ({
            ok: false,
            async json() {
                return {};
            }
        })
    });
    await assert.rejects(() => defaultContext.requestBackupJson("/api/backups"), /Backup request failed/);
});
