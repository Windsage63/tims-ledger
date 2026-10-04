/**
 * @fileoverview Exercise calendar status, edit protection, and payment retry safety.
 * @license Apache-2.0
 * @copyright 2026 Timothy Mallory
 */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function runtime() {
    const windowEvents = {};
    const documentEvents = {};
    const controls = {};
    const field = (id) => controls[id] ||= {
        id, value: '', disabled: false, checked: false, attributes: {}, classes: new Set(), listeners: {},
        classList: { toggle(name, active) { if (active) controls[id].classes.add(name); else controls[id].classes.delete(name); } },
        setAttribute(name, value) { this.attributes[name] = value; },
        addEventListener(name, callback) { this.listeners[name] = callback; }
    };
    const context = vm.createContext({
        Date, Set, Map, URL, URLSearchParams, console,
        setTimeout: () => 0,
        window: {
            addEventListener(name, callback) { (windowEvents[name] ||= []).push(callback); },
            removeEventListener(name, callback) { windowEvents[name] = (windowEvents[name] || []).filter((entry) => entry !== callback); },
            setTimeout: () => 0, setInterval: () => 0, confirm: () => false,
            location: { href: 'http://localhost/frontend/html/time.html', origin: 'http://localhost', pathname: '/frontend/html/time.html', search: '' }
        },
        document: {
            getElementById: field,
            querySelectorAll: () => [],
            addEventListener(name, callback) { (documentEvents[name] ||= []).push(callback); }
        },
        fetch: () => { throw new Error('Unexpected request'); }
    });
    const load = (name) => vm.runInContext(fs.readFileSync(path.join(__dirname, '../frontend/js', name), 'utf8'), context);
    const run = (code) => vm.runInContext(code, context);
    return { context, controls, field, load, run, windowEvents, documentEvents };
}

test('invoice aging follows calendar days, terms, precedence and color boundaries', () => {
    const r = runtime();
    r.load('utils.js');
    for (const [days, classes] of [[1, '30'], [30, '30'], [31, '60'], [60, '60'], [61, '90'], [90, '90'], [91, 'old']]) {
        const issued = new Date(Date.UTC(2026, 9, 4 - days - 30)).toISOString().slice(0, 10);
        const result = r.run(`invoiceDisplayStatus({ status:'printed', invoice_date:'${issued}', terms_days:30, open_balance_cents:1 }, '2026-10-04')`);
        assert.equal(result.label, `Overdue ${days} ${days === 1 ? 'day' : 'days'}`);
        assert.equal(result.classes, `status-overdue-${classes}`);
    }
    for (const status of ['draft', 'new', 'paid']) {
        assert.equal(r.run(`invoiceDisplayStatus({ status:'${status}', invoice_date:'2020-01-01', terms_days:0, open_balance_cents:100 }, '2026-10-04').label`), status === 'paid' ? 'Paid' : 'Draft');
    }
    assert.equal(r.run("invoiceDisplayStatus({ status:'pending', invoice_date:'2026-10-04', terms_days:0, open_balance_cents:1 }, '2026-10-04').label"), 'Open');
    assert.equal(r.run("invoiceDisplayStatus({ status:'pending', invoice_date:'2026-10-03', terms_days:0, open_balance_cents:1 }, '2026-10-04').label"), 'Overdue 1 day');
    assert.equal(r.run("invoiceDisplayStatus({ status:'printed', invoice_date:'2020-01-01', terms_days:0, open_balance_cents:0 }, '2026-10-04').label"), 'Open');
    assert.equal(r.run("invoiceDueDate({ invoice_date:'2024-02-28', terms_days:2 })"), '2024-03-01');
    assert.equal(r.run("invoiceDueDate({ invoice_date:'2026-12-31', terms_days:17 })"), '2027-01-17');
    for (const date of ['2026-02-30', '2026-13-01', '', '10/04/2026']) assert.equal(r.run(`invoiceDueDate({ invoice_date:'${date}', terms_days:30 })`), '');
    assert.equal(r.run("invoiceOverdueDays({ status:'printed', invoice_date:'2026-03-07', terms_days:0, open_balance_cents:1 }, '2026-03-09')"), 2);
    assert.equal(r.run("invoiceOverdueDays({ status:'printed', invoice_date:'2026-03-07', terms_days:0 }, '2026-03-09')"), 0);
});

test('protection preserves canceled drafts, restores on relock, and resets after save or cached return', () => {
    const r = runtime();
    r.load('editor-protection.js');
    r.run(`let model = { id: 1, value: 'saved' }; let saving = false;
        editorProtection.register({ formId:'test-form', recordId:()=>model.id, busy:()=>saving,
            snapshot:()=>model.value, capture:()=>model, restore:(saved)=>{model=saved;}, render:()=>editorProtection.refresh() });`);
    r.windowEvents.DOMContentLoaded.forEach((callback) => callback());
    const toggle = r.field('edit-mode-button').listeners.click;
    assert.equal(r.run('editorProtection.canWrite()'), false);
    toggle();
    r.run("model.value='changed'");
    assert.equal(r.run('editorProtection.dirty()'), true);
    assert.equal(r.run('editorProtection.allowTransition()'), false);
    toggle();
    assert.equal(r.run('model.value'), 'changed');
    assert.equal(r.run('editorProtection.canWrite()'), true);
    r.context.window.confirm = () => true;
    toggle();
    assert.equal(r.run('model.value'), 'saved');
    assert.equal(r.run('editorProtection.canWrite()'), false);
    toggle();
    r.run("model.value='saved again'; editorProtection.saved()");
    assert.equal(r.run('editorProtection.dirty()'), false);
    assert.equal(r.run('editorProtection.canWrite()'), false);
    toggle();
    r.windowEvents.pageshow.forEach((callback) => callback());
    assert.equal(r.run('editorProtection.canWrite()'), false);
    r.run("model={id:null,value:'new'};editorProtection.accept()");
    assert.equal(r.run('editorProtection.canWrite()'), true);
    assert.equal(r.run('editorProtection.dirty()'), false);
    r.run('editorProtection.accept({duplicate:true})');
    assert.equal(r.run('editorProtection.dirty()'), true);
    r.run('saving=true');
    assert.equal(r.run('editorProtection.allowTransition()'), false);
});

test('dirty tracking becomes clean again when changes are reverted', () => {
    const r = runtime();
    r.load('editor-protection.js');
    r.run(`let value = 'original'; editorProtection.register({ formId:'test', recordId:()=>1, busy:()=>false,
        snapshot:()=>value, capture:()=>value, restore:()=>{}, render:()=>{} });
        value='modified';editorProtection.refresh();`);
    assert.equal(r.run('editorProtection.dirty()'), true);
    assert.equal(r.windowEvents.beforeunload.length, 1);
    r.run("value='original';editorProtection.refresh()");
    assert.equal(r.run('editorProtection.dirty()'), false);
    assert.equal(r.windowEvents.beforeunload.length, 0);
});

test('a partial create gaining an ID does not silently accept the unsaved draft', () => {
    const r = runtime();
    r.load('editor-protection.js');
    r.run(`let model={id:null,value:'blank'};editorProtection.register({formId:'test',recordId:()=>model.id,busy:()=>false,
        snapshot:()=>model.value,capture:()=>model,restore:()=>{},render:()=>{}});
        model.value='intended allocation';model.id=77;editorProtection.enableRetry();editorProtection.refresh();`);
    assert.equal(r.run('editorProtection.dirty()'), true);
    assert.equal(r.run('editorProtection.canWrite()'), true);
});

test('protected invoice printing only reads the saved document', async () => {
    const r = runtime();
    r.context.editorProtection = { canWrite: () => false };
    r.context.showToast = (message) => { throw new Error(message); };
    const requests = [];
    let printed = '';
    r.context.fetch = async (url, options) => { requests.push([url, options?.method || 'GET']); return { ok: true }; };
    r.context.window.open = () => ({ close() {}, location: { replace(url) { printed = url; } } });
    r.load('invoices.js');
    r.run("invoicesState.editor.invoice={id:42,pdf_file_name:'invoices/saved.html'}");
    await r.run('savePrintInvoice()');
    assert.deepEqual(requests, [['/api/invoices/42/document?autoprint=1', 'GET']]);
    assert.equal(printed, '/api/invoices/42/document?autoprint=1');
});

test('invoice and payment drafts do not mutate saved browse records', () => {
    for (const screen of ['invoices', 'payments']) {
        const r = runtime();
        r.load('utils.js');
        r.context.cloneEditorData = (value) => JSON.parse(JSON.stringify(value));
        r.context.editorProtection = { canWrite: () => true };
        r.load(`${screen}.js`);
        if (screen === 'invoices') {
            for (const [id, value] of Object.entries({ 'invoice-number': 'changed', 'invoice-project': '1', 'invoice-date': '2026-10-04', 'invoice-terms': '30', 'invoice-notes': 'changed' })) r.field(id).value = value;
            r.run(`const original={id:1,invoice_number:'saved',project_id:1,invoice_date:'2026-10-03',terms_days:15,notes:'saved'};
                invoicesState.invoices=[original];setEditorPayload({invoice:original});syncSelectedInvoiceFromForm();`);
            assert.equal(r.run('invoicesState.invoices[0].invoice_number'), 'saved');
            assert.equal(r.run('invoicesState.invoices[0].terms_days'), 15);
            assert.equal(r.run('selectedInvoice().invoice_number'), 'changed');
        } else {
            for (const [id, value] of Object.entries({ 'payment-reference': 'changed', 'payment-customer': '1', 'payment-date': '2026-10-04', 'payment-amount': '60.00', 'payment-notes': 'changed' })) r.field(id).value = value;
            r.run(`setEditorPayload({payment:{id:1,customer_id:1,reference_number:'saved',payment_date:'2026-10-03',amount_cents:5000,notes:'saved'}});syncSelectedPaymentFromForm();`);
            assert.equal(r.run('paymentsState.payments[0].reference_number'), 'saved');
            assert.equal(r.run('paymentsState.payments[0].amount_cents'), 5000);
            assert.equal(r.run('selectedPayment().amount_cents'), 6000);
        }
    }
});

test('app navigation cancellation keeps a dirty draft and confirmed navigation avoids a second unload prompt', () => {
    const r = runtime();
    r.load('editor-protection.js');
    r.run(`let value='saved';editorProtection.register({formId:'test',recordId:()=>1,busy:()=>false,
        snapshot:()=>value,capture:()=>value,restore:()=>{},render:()=>{}});value='changed';editorProtection.refresh();`);
    let prevented = false;
    const event = { target: { closest: () => ({ href: 'http://localhost/frontend/html/expenses.html', target: '', hasAttribute: () => false }) },
        button: 0, preventDefault() { prevented = true; }, stopImmediatePropagation() {} };
    r.documentEvents.click[0](event);
    assert.equal(prevented, true);
    assert.equal(r.run('value'), 'changed');
    assert.equal(r.windowEvents.beforeunload.length, 1);
    r.context.window.confirm = () => true;
    prevented = false;
    r.documentEvents.click[0](event);
    assert.equal(prevented, false);
    assert.equal(r.windowEvents.beforeunload.length, 0);
});

test('saved-record save handlers and payment application helper refuse writes while protected', async () => {
    for (const [file, action] of [['customers.js', 'saveCustomer({preventDefault(){}})'], ['projects.js', 'saveProject({preventDefault(){}})'], ['time.js', 'saveEntry({preventDefault(){}})'], ['expenses.js', 'saveExpense({preventDefault(){}})'], ['payments.js', 'savePayment()']]) {
        const r = runtime();
        r.context.editorProtection = { canWrite: () => false };
        r.load(file);
        if (file === 'payments.js') r.run('paymentsState.editor.payment={id:1}');
        await r.run(action);
    }
    const r = runtime();
    r.context.editorProtection = { canWrite: () => false };
    r.context.showToast = () => {};
    r.load('invoices.js');
    r.run('invoicesState.editor.invoice={id:1};render=()=>{}');
    await r.run('savePrintInvoice()'); // Missing saved document explains what to do; no POST.
    r.load('payments.js');
    await assert.rejects(r.run('saveApplicationsForPayment(1)'), /Use Save Payment/);
});

test('partial new-payment allocation failure keeps the created ID and retries with PUT', async () => {
    const r = runtime();
    r.load('utils.js');
    r.context.cloneEditorData = (value) => JSON.parse(JSON.stringify(value));
    let savedCount = 0;
    r.context.editorProtection = { canWrite: () => true, accept: () => {}, enableRetry: () => {}, saved: () => { savedCount++; } };
    r.context.showToast = () => {};
    r.load('payments.js');
    r.run(`render=()=>{};paymentsState.isLoading=false;
        paymentsState.editor.payment={id:null,customer_id:1,payment_date:'2026-10-04',reference_number:'test',amount_cents:5000,notes:''};
        paymentsState.editor.open_invoices=[{id:2,current_applied_cents:0,available_to_apply_cents:10000}];
        paymentsState.applicationDrafts={2:2500};`);
    for (const [id, value] of Object.entries({ 'payment-customer': '1', 'payment-date': '2026-10-04', 'payment-reference': 'test', 'payment-amount': '50.00', 'payment-notes': '' })) r.field(id).value = value;
    const calls = [];
    let fail = true;
    r.context.requestJson = undefined;
    r.run('requestJson=(...args)=>testRequest(...args)');
    r.context.testRequest = async (route, options = {}) => {
        calls.push([route, options.method || 'GET']);
        if (route === '/bootstrap') return {business_summary: {total_income_cents:5000,total_open_ar_cents:10000,total_expenses_cents:0,non_billable_expenses_cents:0}};
        if (route.endsWith('/applications') && fail) { fail = false; throw new Error('allocation failure'); }
        const payment = { id: 77, customer_id: 1, payment_date: '2026-10-04', reference_number: 'test', amount_cents: 5000, notes: '' };
        return { payment, applications: [], open_invoices: [{ id: 2, current_applied_cents: 0, available_to_apply_cents: 10000 }] };
    };
    await r.run('savePayment()');
    assert.equal(r.run('selectedPayment().id'), 77);
    assert.equal(r.run('paymentsState.applicationDrafts[2]'), 2500);
    assert.equal(savedCount, 0);
    await r.run('savePayment()');
    assert.equal(calls.filter(([route, method]) => route === '' && method === 'POST').length, 1);
    assert.ok(calls.some(([route, method]) => route === '/77' && method === 'PUT'));
    assert.equal(savedCount, 1);
    assert.equal(calls.filter(([route]) => route === '/bootstrap').length, 2);
    assert.equal(r.field('metric-total-income').textContent, '$50.00');
});


test('business totals ignore ledger filters and refresh without replacing a payment draft', async () => {
    const r = runtime();
    r.load('utils.js');
    r.context.showToast = () => {};
    r.context.editorProtection = { accept: () => { throw new Error('Totals must not accept an editor baseline'); } };
    r.load('payments.js');
    r.run(`paymentsState.businessSummary={total_income_cents:15000,total_open_ar_cents:9000,total_expenses_cents:5000,non_billable_expenses_cents:2000};
        paymentsState.payments=[{id:1,customer_id:1,customer_name:'Alpha',payment_date:'2025-01-01',amount_cents:8000,application_status:'partially_applied'}];
        paymentsState.editor.payment={id:99,amount_cents:99999};paymentsState.applicationDrafts={2:1234};
        paymentsState.searchQuery='no match';paymentsState.customerFilter='2';paymentsState.yearFilter='2026';paymentsState.statusFilter='fully_applied';
        renderMetrics();`);
    assert.equal(r.run('filteredPayments().length'), 0);
    assert.equal(r.field('metric-total-income').textContent, '$150.00');
    assert.equal(r.field('metric-open-ar').textContent, '$90.00');
    assert.equal(r.field('metric-total-expenses').textContent, '$50.00');
    assert.equal(r.field('metric-non-billable-expenses').textContent, '$20.00');
    const calls = [];
    r.run('requestJson=(...args)=>testRequest(...args)');
    r.context.testRequest = async (route, options) => {
        calls.push([route, options]);
        return { payments: [], business_summary: {total_income_cents:16000,total_open_ar_cents:6000,total_expenses_cents:5000,non_billable_expenses_cents:2000} };
    };
    await r.run('refreshBusinessSummary()');
    assert.equal(calls[0][0], '/bootstrap');
    assert.equal(Object.keys(calls[0][1]).length, 0);
    assert.equal(r.field('metric-total-income').textContent, '$160.00');
    assert.equal(r.field('metric-open-ar').textContent, '$60.00');
    assert.equal(r.run('selectedPayment().amount_cents'), 99999);
    assert.equal(r.run('paymentsState.applicationDrafts[2]'), 1234);
    assert.equal(r.run('paymentsState.payments.length'), 1);
    assert.equal(r.run('paymentsState.yearFilter'), '2026');
    r.context.testRequest = async () => { throw new Error('offline'); };
    await r.run('refreshBusinessSummary()');
    for (const id of ['metric-total-income', 'metric-open-ar', 'metric-total-expenses', 'metric-non-billable-expenses']) assert.equal(r.field(id).textContent, '—');
    assert.equal(r.run('selectedPayment().amount_cents'), 99999);
});
