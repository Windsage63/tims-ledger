import {
  Activity,
  BadgeDollarSign,
  BookOpenCheck,
  BriefcaseBusiness,
  Building2,
  Clock3,
  DatabaseBackup,
  FileInput,
  FileText,
  Plus,
  ReceiptText,
  RefreshCw,
  WalletCards,
} from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import {
  createInvoice,
  createCustomer,
  createExpense,
  createExpenseCategory,
  createProject,
  createTimeEntry,
  getInvoiceCandidates,
  getHealth,
  issueInvoice,
  listExpenseCategories,
  listExpenses,
  listInvoices,
  listCustomers,
  listProjects,
  listTimeEntries,
  type ApiHealth,
  type Customer,
  type Expense,
  type ExpenseCategory,
  type Invoice,
  type InvoiceCandidates,
  type InvoiceDetail,
  type Project,
  type TimeEntry,
} from "./api";

const navItems = [
  { label: "Customers", icon: Building2, key: "customers" },
  { label: "Projects", icon: BriefcaseBusiness, key: "projects" },
  { label: "Time", icon: Clock3, key: "time" },
  { label: "Expenses", icon: ReceiptText, key: "expenses" },
  { label: "Invoices", icon: FileText, key: "invoices" },
  { label: "Payments", icon: WalletCards, key: "payments" },
  { label: "Reports", icon: BadgeDollarSign, key: "reports" },
  { label: "Imports", icon: FileInput, key: "imports" },
  { label: "Backups", icon: DatabaseBackup, key: "backups" },
] as const;

type SectionKey = (typeof navItems)[number]["key"];

const sectionTitles: Record<SectionKey, string> = {
  customers: "Customers",
  projects: "Projects",
  time: "Time",
  expenses: "Expenses",
  invoices: "Invoices",
  payments: "Payments",
  reports: "Reports",
  imports: "Imports",
  backups: "Backups",
};

export default function App() {
  const [activeSection, setActiveSection] = useState<SectionKey>("customers");
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([]);
  const [expenseCategories, setExpenseCategories] = useState<ExpenseCategory[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [dataError, setDataError] = useState<string | null>(null);
  const [customerName, setCustomerName] = useState("");
  const [customerContactName, setCustomerContactName] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [customerAddressLine1, setCustomerAddressLine1] = useState("");
  const [customerAddressLine2, setCustomerAddressLine2] = useState("");
  const [customerCity, setCustomerCity] = useState("");
  const [customerState, setCustomerState] = useState("");
  const [customerPostalCode, setCustomerPostalCode] = useState("");
  const [customerTerms, setCustomerTerms] = useState("Due on receipt");
  const [customerNotes, setCustomerNotes] = useState("");
  const [customerActive, setCustomerActive] = useState(true);
  const [projectNo, setProjectNo] = useState("");
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [projectCustomerId, setProjectCustomerId] = useState("");
  const [projectRate, setProjectRate] = useState("125.00");
  const [projectFixedFee, setProjectFixedFee] = useState("");
  const [timeProjectId, setTimeProjectId] = useState("");
  const [timeDate, setTimeDate] = useState(new Date().toISOString().slice(0, 10));
  const [timeDescription, setTimeDescription] = useState("");
  const [timeHours, setTimeHours] = useState("1.00");
  const [timeWorkType, setTimeWorkType] = useState("");
  const [timeBillable, setTimeBillable] = useState(true);
  const [categoryName, setCategoryName] = useState("");
  const [expenseProjectId, setExpenseProjectId] = useState("");
  const [expenseCategoryId, setExpenseCategoryId] = useState("");
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().slice(0, 10));
  const [expenseDescription, setExpenseDescription] = useState("");
  const [expenseVendor, setExpenseVendor] = useState("");
  const [expenseQty, setExpenseQty] = useState("1.00");
  const [expenseUnitCost, setExpenseUnitCost] = useState("0.00");
  const [invoiceCustomerId, setInvoiceCustomerId] = useState("");
  const [invoiceProjectId, setInvoiceProjectId] = useState("");
  const [invoiceNo, setInvoiceNo] = useState("662");
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().slice(0, 10));
  const [invoiceTerms, setInvoiceTerms] = useState("Due on receipt");
  const [invoiceCandidates, setInvoiceCandidates] = useState<InvoiceCandidates | null>(null);
  const [selectedTimeEntryIds, setSelectedTimeEntryIds] = useState<number[]>([]);
  const [selectedExpenseIds, setSelectedExpenseIds] = useState<number[]>([]);
  const [workingInvoice, setWorkingInvoice] = useState<InvoiceDetail | null>(null);
  const [invoiceRegister, setInvoiceRegister] = useState<Invoice[]>([]);

  useEffect(() => {
    let alive = true;

    getHealth()
      .then((result) => {
        if (alive) {
          setHealth(result);
          setHealthError(null);
        }
      })
      .catch((error: unknown) => {
        if (alive) {
          setHealth(null);
          setHealthError(error instanceof Error ? error.message : "Unable to reach API");
        }
      });

    return () => {
      alive = false;
    };
  }, []);

  const refreshData = async () => {
    try {
      const [customerRows, projectRows, timeRows, categoryRows, expenseRows] = await Promise.all([
        listCustomers(),
        listProjects(),
        listTimeEntries(),
        listExpenseCategories(),
        listExpenses(),
      ]);
      setCustomers(customerRows);
      setProjects(projectRows);
      setTimeEntries(timeRows);
      setExpenseCategories(categoryRows);
      setExpenses(expenseRows);
      setDataError(null);
      if (!projectCustomerId && customerRows[0]) {
        setProjectCustomerId(String(customerRows[0].id));
      }
      if (!timeProjectId && projectRows[0]) {
        setTimeProjectId(String(projectRows[0].id));
      }
      if (!expenseProjectId && projectRows[0]) {
        setExpenseProjectId(String(projectRows[0].id));
      }
      if (!expenseCategoryId && categoryRows[0]) {
        setExpenseCategoryId(String(categoryRows[0].id));
      }
      if (!invoiceCustomerId && customerRows[0]) {
        setInvoiceCustomerId(String(customerRows[0].id));
        setInvoiceTerms(customerRows[0].default_terms);
      }
    } catch (error) {
      setDataError(error instanceof Error ? error.message : "Unable to load records");
    }
  };

  useEffect(() => {
    void refreshData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const apiStatus = useMemo(() => {
    if (health) {
      return { label: "Connected", tone: "online" };
    }
    if (healthError) {
      return { label: "Offline", tone: "offline" };
    }
    return { label: "Checking", tone: "pending" };
  }, [health, healthError]);

  const customerNameById = new Map(customers.map((customer) => [customer.id, customer.name]));
  const projectNameById = new Map(projects.map((project) => [project.id, project.name]));
  const categoryNameById = new Map(
    expenseCategories.map((category) => [category.id, category.name]),
  );
  const selectedTimeProject = useMemo(
    () => projects.find((project) => String(project.id) === timeProjectId),
    [projects, timeProjectId],
  );
  const timeCodeOptions = useMemo(
    () => buildTimeCodeOptions(selectedTimeProject),
    [selectedTimeProject],
  );
  const invoiceProjects = useMemo(() => {
    if (!invoiceCustomerId) {
      return projects;
    }
    return projects.filter((project) => project.customer_id === Number(invoiceCustomerId));
  }, [invoiceCustomerId, projects]);

  useEffect(() => {
    if (!invoiceCustomerId) {
      setInvoiceProjectId("");
      return;
    }
    if (invoiceProjectId && invoiceProjects.some((project) => String(project.id) === invoiceProjectId)) {
      return;
    }
    setInvoiceProjectId(invoiceProjects[0] ? String(invoiceProjects[0].id) : "");
  }, [invoiceCustomerId, invoiceProjectId, invoiceProjects]);

  useEffect(() => {
    setWorkingInvoice(null);
    setSelectedTimeEntryIds([]);
    setSelectedExpenseIds([]);
  }, [invoiceCustomerId, invoiceProjectId]);

  useEffect(() => {
    if (timeCodeOptions.length === 0) {
      if (timeWorkType) {
        setTimeWorkType("");
      }
      return;
    }
    if (!timeCodeOptions.some((option) => option.code === timeWorkType)) {
      setTimeWorkType(timeCodeOptions[0]?.code ?? "");
    }
  }, [timeCodeOptions, timeWorkType]);

  const loadInvoiceWorkspace = async (customerId: string, projectId: string) => {
    if (!customerId || !projectId) {
      return null;
    }
    const [candidates, invoices] = await Promise.all([
      getInvoiceCandidates({
        customer_id: Number(customerId),
        project_id: Number(projectId),
      }),
      listInvoices({ customer_id: Number(customerId) }),
    ]);
    return { candidates, invoices };
  };

  useEffect(() => {
    if (activeSection !== "invoices") {
      return;
    }
    if (!invoiceCustomerId || !invoiceProjectId) {
      setInvoiceCandidates(null);
      setInvoiceRegister([]);
      return;
    }

    let alive = true;

    void loadInvoiceWorkspace(invoiceCustomerId, invoiceProjectId)
      .then((workspace) => {
        if (!alive || workspace === null) {
          return;
        }
        setInvoiceCandidates(workspace.candidates);
        setInvoiceRegister(workspace.invoices);
        setDataError(null);
      })
      .catch((error: unknown) => {
        if (!alive) {
          return;
        }
        setDataError(error instanceof Error ? error.message : "Unable to load invoice workspace");
      });

    return () => {
      alive = false;
    };
  }, [activeSection, invoiceCustomerId, invoiceProjectId]);

  const submitCustomer = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!customerName.trim()) {
      return;
    }
    try {
      await createCustomer({
        name: customerName.trim(),
        billing_contact_name: customerContactName.trim() || null,
        billing_email: customerEmail.trim() || null,
        phone: customerPhone.trim() || null,
        billing_address_line1: customerAddressLine1.trim() || null,
        billing_address_line2: customerAddressLine2.trim() || null,
        billing_city: customerCity.trim() || null,
        billing_state: customerState.trim() || null,
        billing_postal_code: customerPostalCode.trim() || null,
        default_terms: customerTerms.trim() || "Due on receipt",
        notes: customerNotes.trim() || null,
        active: customerActive,
      });
      setCustomerName("");
      setCustomerContactName("");
      setCustomerEmail("");
      setCustomerPhone("");
      setCustomerAddressLine1("");
      setCustomerAddressLine2("");
      setCustomerCity("");
      setCustomerState("");
      setCustomerPostalCode("");
      setCustomerTerms("Due on receipt");
      setCustomerNotes("");
      setCustomerActive(true);
      await refreshData();
    } catch (error) {
      setDataError(error instanceof Error ? error.message : "Unable to create customer");
    }
  };

  const submitProject = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!projectNo.trim() || !projectName.trim() || !projectCustomerId) {
      return;
    }
    try {
      await createProject({
        customer_id: Number(projectCustomerId),
        project_no: projectNo.trim(),
        name: projectName.trim(),
        description: projectDescription.trim() || null,
        contract_type: "time_and_materials",
        status: "active",
        default_hourly_rate: projectRate.trim() || null,
        fixed_fee_amount: projectFixedFee.trim() || null,
      });
      setProjectNo("");
      setProjectName("");
      setProjectDescription("");
      setProjectFixedFee("");
      await refreshData();
    } catch (error) {
      setDataError(error instanceof Error ? error.message : "Unable to create project");
    }
  };

  const submitTimeEntry = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!timeProjectId || !timeDescription.trim()) {
      return;
    }
    const selectedTimeCode = timeCodeOptions.find((option) => option.code === timeWorkType);
    try {
      await createTimeEntry({
        date: timeDate,
        project_id: Number(timeProjectId),
        description: timeDescription.trim(),
        hours: timeHours,
        work_type: timeWorkType.trim() || null,
        rate: selectedTimeCode?.rate ?? null,
        billable: timeBillable,
      });
      setTimeDescription("");
      setTimeWorkType(timeCodeOptions[0]?.code ?? "");
      setTimeBillable(true);
      await refreshData();
    } catch (error) {
      setDataError(error instanceof Error ? error.message : "Unable to create time entry");
    }
  };

  const submitExpenseCategory = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!categoryName.trim()) {
      return;
    }
    try {
      await createExpenseCategory({ name: categoryName.trim() });
      setCategoryName("");
      await refreshData();
    } catch (error) {
      setDataError(error instanceof Error ? error.message : "Unable to create expense category");
    }
  };

  const submitExpense = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!expenseProjectId || !expenseDescription.trim()) {
      return;
    }
    try {
      await createExpense({
        date: expenseDate,
        project_id: Number(expenseProjectId),
        vendor: expenseVendor.trim() || null,
        description: expenseDescription.trim(),
        qty: expenseQty,
        unit_cost: expenseUnitCost,
        category_id: expenseCategoryId ? Number(expenseCategoryId) : null,
        billable: true,
        reimbursable: true,
      });
      setExpenseDescription("");
      setExpenseVendor("");
      setExpenseUnitCost("0.00");
      await refreshData();
    } catch (error) {
      setDataError(error instanceof Error ? error.message : "Unable to create expense");
    }
  };

  const submitInvoice = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!invoiceCustomerId || !invoiceProjectId || !invoiceNo.trim()) {
      return;
    }
    if (selectedTimeEntryIds.length === 0 && selectedExpenseIds.length === 0) {
      setDataError("Select at least one time entry or expense before creating an invoice.");
      return;
    }

    try {
      const invoice = await createInvoice({
        invoice_no: invoiceNo.trim(),
        customer_id: Number(invoiceCustomerId),
        invoice_date: invoiceDate,
        time_entry_ids: selectedTimeEntryIds,
        expense_ids: selectedExpenseIds,
        terms: invoiceTerms,
      });
      setWorkingInvoice(invoice);
      setSelectedTimeEntryIds([]);
      setSelectedExpenseIds([]);
      setInvoiceNo(nextInvoiceNo(invoiceNo));
      await refreshData();
      const workspace = await loadInvoiceWorkspace(invoiceCustomerId, invoiceProjectId);
      if (workspace) {
        setInvoiceCandidates(workspace.candidates);
        setInvoiceRegister(workspace.invoices);
      }
      setDataError(null);
    } catch (error) {
      setDataError(error instanceof Error ? error.message : "Unable to create invoice");
    }
  };

  const publishInvoice = async () => {
    if (!workingInvoice) {
      return;
    }

    try {
      const invoice = await issueInvoice(workingInvoice.id, { sent_date: invoiceDate });
      setWorkingInvoice(invoice);
      await refreshData();
      const workspace = await loadInvoiceWorkspace(invoiceCustomerId, invoiceProjectId);
      if (workspace) {
        setInvoiceCandidates(workspace.candidates);
        setInvoiceRegister(workspace.invoices);
      }
      setDataError(null);
    } catch (error) {
      setDataError(error instanceof Error ? error.message : "Unable to issue invoice");
    }
  };

  const toggleTimeEntrySelection = (entryId: number) => {
    setSelectedTimeEntryIds((current) =>
      current.includes(entryId)
        ? current.filter((value) => value !== entryId)
        : [...current, entryId],
    );
  };

  const toggleExpenseSelection = (expenseId: number) => {
    setSelectedExpenseIds((current) =>
      current.includes(expenseId)
        ? current.filter((value) => value !== expenseId)
        : [...current, expenseId],
    );
  };

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <BookOpenCheck aria-hidden="true" size={28} />
          <div>
            <strong>Windsage Ledger</strong>
            <span>Simple books I can understand.</span>
          </div>
        </div>

        <nav className="nav-list">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={activeSection === item.key ? "nav-item active" : "nav-item"}
                key={item.key}
                onClick={() => setActiveSection(item.key)}
                title={item.label}
                type="button"
              >
                <Icon aria-hidden="true" size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Local-first accounting workspace</p>
            <h1>{sectionTitles[activeSection]}</h1>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" onClick={() => void refreshData()} title="Refresh" type="button">
              <RefreshCw aria-hidden="true" size={17} />
            </button>
            <div className={`api-status ${apiStatus.tone}`}>
              <Activity aria-hidden="true" size={18} />
              <span>{apiStatus.label}</span>
            </div>
          </div>
        </header>

        {dataError ? <div className="error-banner">{dataError}</div> : null}

        {activeSection === "customers" ? (
          <CustomersView
            customerActive={customerActive}
            customerAddressLine1={customerAddressLine1}
            customerAddressLine2={customerAddressLine2}
            customerCity={customerCity}
            customerContactName={customerContactName}
            customerEmail={customerEmail}
            customerName={customerName}
            customerNotes={customerNotes}
            customerPhone={customerPhone}
            customerPostalCode={customerPostalCode}
            customerState={customerState}
            customerTerms={customerTerms}
            customers={customers}
            onActiveChange={setCustomerActive}
            onAddressLine1Change={setCustomerAddressLine1}
            onAddressLine2Change={setCustomerAddressLine2}
            onCityChange={setCustomerCity}
            onContactNameChange={setCustomerContactName}
            onEmailChange={setCustomerEmail}
            onNameChange={setCustomerName}
            onNotesChange={setCustomerNotes}
            onPhoneChange={setCustomerPhone}
            onPostalCodeChange={setCustomerPostalCode}
            onStateChange={setCustomerState}
            onSubmit={submitCustomer}
            onTermsChange={setCustomerTerms}
          />
        ) : null}

        {activeSection === "projects" ? (
          <ProjectsView
            customerNameById={customerNameById}
            customers={customers}
            onCustomerChange={setProjectCustomerId}
            onDescriptionChange={setProjectDescription}
            onFixedFeeChange={setProjectFixedFee}
            onNameChange={setProjectName}
            onProjectNoChange={setProjectNo}
            onRateChange={setProjectRate}
            onSubmit={submitProject}
            projectCustomerId={projectCustomerId}
            projectDescription={projectDescription}
            projectFixedFee={projectFixedFee}
            projectName={projectName}
            projectNo={projectNo}
            projectRate={projectRate}
            projects={projects}
          />
        ) : null}

        {activeSection === "time" ? (
          <TimeEntriesView
            onDateChange={setTimeDate}
            onDescriptionChange={setTimeDescription}
            onHoursChange={setTimeHours}
            onBillableChange={setTimeBillable}
            onProjectChange={setTimeProjectId}
            onSubmit={submitTimeEntry}
            onWorkTypeChange={setTimeWorkType}
            projectNameById={projectNameById}
            projects={projects}
            timeBillable={timeBillable}
            timeCodeOptions={timeCodeOptions}
            timeDate={timeDate}
            timeDescription={timeDescription}
            timeEntries={timeEntries}
            timeHours={timeHours}
            timeProjectId={timeProjectId}
            timeWorkType={timeWorkType}
          />
        ) : null}

        {activeSection === "expenses" ? (
          <ExpensesView
            categoryName={categoryName}
            categoryNameById={categoryNameById}
            expenseCategories={expenseCategories}
            expenseCategoryId={expenseCategoryId}
            expenseDate={expenseDate}
            expenseDescription={expenseDescription}
            expenseProjectId={expenseProjectId}
            expenseQty={expenseQty}
            expenseUnitCost={expenseUnitCost}
            expenseVendor={expenseVendor}
            expenses={expenses}
            onCategoryChange={setExpenseCategoryId}
            onCategoryNameChange={setCategoryName}
            onCategorySubmit={submitExpenseCategory}
            onDateChange={setExpenseDate}
            onDescriptionChange={setExpenseDescription}
            onProjectChange={setExpenseProjectId}
            onQtyChange={setExpenseQty}
            onSubmit={submitExpense}
            onUnitCostChange={setExpenseUnitCost}
            onVendorChange={setExpenseVendor}
            projectNameById={projectNameById}
            projects={projects}
          />
        ) : null}

        {activeSection === "invoices" ? (
          <InvoicesView
            customers={customers}
            invoiceCandidates={invoiceCandidates}
            invoiceCustomerId={invoiceCustomerId}
            invoiceDate={invoiceDate}
            invoiceNo={invoiceNo}
            invoiceProjectId={invoiceProjectId}
            invoiceProjects={invoiceProjects}
            invoiceRegister={invoiceRegister}
            invoiceTerms={invoiceTerms}
            onCustomerChange={(value) => {
              setInvoiceCustomerId(value);
              const customer = customers.find((row) => String(row.id) === value);
              if (customer) {
                setInvoiceTerms(customer.default_terms);
              }
            }}
            onDateChange={setInvoiceDate}
            onIssue={publishInvoice}
            onInvoiceNoChange={setInvoiceNo}
            onProjectChange={setInvoiceProjectId}
            onSubmit={submitInvoice}
            onTermsChange={setInvoiceTerms}
            onToggleExpense={toggleExpenseSelection}
            onToggleTime={toggleTimeEntrySelection}
            selectedExpenseIds={selectedExpenseIds}
            selectedTimeEntryIds={selectedTimeEntryIds}
            workingInvoice={workingInvoice}
          />
        ) : null}

        {!["customers", "projects", "time", "expenses", "invoices"].includes(activeSection) ? (
          <section className="panel empty-state">
            <p className="eyebrow">Roadmap area</p>
            <h2>{sectionTitles[activeSection]} workflow</h2>
            <p>This screen is next after customers and projects are fully usable.</p>
          </section>
        ) : null}
      </main>
    </div>
  );
}

function InvoicesView(props: {
  customers: Customer[];
  invoiceCandidates: InvoiceCandidates | null;
  invoiceCustomerId: string;
  invoiceDate: string;
  invoiceNo: string;
  invoiceProjectId: string;
  invoiceProjects: Project[];
  invoiceRegister: Invoice[];
  invoiceTerms: string;
  onCustomerChange: (value: string) => void;
  onDateChange: (value: string) => void;
  onIssue: () => void;
  onInvoiceNoChange: (value: string) => void;
  onProjectChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onTermsChange: (value: string) => void;
  onToggleExpense: (expenseId: number) => void;
  onToggleTime: (entryId: number) => void;
  selectedExpenseIds: number[];
  selectedTimeEntryIds: number[];
  workingInvoice: InvoiceDetail | null;
}) {
  const selectedLabor = props.invoiceCandidates?.time_entries
    .filter((entry) => props.selectedTimeEntryIds.includes(entry.id))
    .reduce((sum, entry) => sum + Number(entry.hours) * Number(entry.rate), 0) ?? 0;
  const selectedExpenses = props.invoiceCandidates?.expenses
    .filter((expense) => props.selectedExpenseIds.includes(expense.id))
    .reduce((sum, expense) => sum + Number(expense.total), 0) ?? 0;
  const selectedTotal = selectedLabor + selectedExpenses;

  return (
    <section className="stacked-panels">
      <section className="record-layout invoice-layout">
        <form className="panel form-panel" onSubmit={props.onSubmit}>
          <p className="eyebrow">Working invoice</p>
          <label>
            <span>Customer</span>
            <select
              onChange={(event) => props.onCustomerChange(event.target.value)}
              value={props.invoiceCustomerId}
            >
              <option value="">Select customer</option>
              {props.customers.map((customer) => (
                <option key={customer.id} value={customer.id}>
                  {customer.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Project</span>
            <select
              onChange={(event) => props.onProjectChange(event.target.value)}
              value={props.invoiceProjectId}
            >
              <option value="">Select project</option>
              {props.invoiceProjects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </label>
          <div className="form-grid">
            <label>
              <span>Invoice number</span>
              <input
                onChange={(event) => props.onInvoiceNoChange(event.target.value)}
                value={props.invoiceNo}
              />
            </label>
            <label>
              <span>Invoice date</span>
              <input
                onChange={(event) => props.onDateChange(event.target.value)}
                type="date"
                value={props.invoiceDate}
              />
            </label>
          </div>
          <label>
            <span>Terms</span>
            <input
              onChange={(event) => props.onTermsChange(event.target.value)}
              value={props.invoiceTerms}
            />
          </label>
          <div className="selection-summary">
            <span>{props.selectedTimeEntryIds.length} time rows selected</span>
            <span>{props.selectedExpenseIds.length} expense rows selected</span>
            <strong>${formatMoney(selectedTotal)}</strong>
          </div>
          <button className="primary-button" type="submit">
            <Plus aria-hidden="true" size={17} />
            <span>Create Draft Invoice</span>
          </button>
          <button
            className="secondary-button"
            disabled={props.workingInvoice === null || props.workingInvoice.status !== "draft"}
            onClick={props.onIssue}
            type="button"
          >
            <FileText aria-hidden="true" size={17} />
            <span>Issue Current Invoice</span>
          </button>
        </form>

        <section className="stacked-panels">
          <SelectableRecordTable
            columns={["Date", "Description", "Hours", "Rate", "Amount"]}
            rows={(props.invoiceCandidates?.time_entries ?? []).map((entry) => ({
              cells: [
                entry.date,
                entry.description,
                entry.hours,
                entry.rate,
                formatMoney(Number(entry.hours) * Number(entry.rate)),
              ],
              key: `time-${entry.id}`,
              onToggle: () => props.onToggleTime(entry.id),
              selected: props.selectedTimeEntryIds.includes(entry.id),
            }))}
            title="Eligible Time"
          />
          <SelectableRecordTable
            columns={["Date", "Description", "Vendor", "Total"]}
            rows={(props.invoiceCandidates?.expenses ?? []).map((expense) => ({
              cells: [expense.date, expense.description, expense.vendor ?? "", expense.total],
              key: `expense-${expense.id}`,
              onToggle: () => props.onToggleExpense(expense.id),
              selected: props.selectedExpenseIds.includes(expense.id),
            }))}
            title="Eligible Expenses"
          />
        </section>
      </section>

      <section className="record-layout invoice-layout">
        <RecordTable
          columns={["Source", "Description", "Qty", "Unit", "Amount"]}
          rows={(props.workingInvoice?.lines ?? []).map((line) => [
            line.source_type ?? "manual",
            line.description,
            line.qty,
            line.unit_price,
            line.amount,
          ])}
          title={props.workingInvoice ? `Invoice ${props.workingInvoice.invoice_no}` : "Current Invoice"}
        />

        <RecordTable
          columns={["Invoice", "Status", "Invoice date", "Published", "Total", "Open balance"]}
          rows={props.invoiceRegister.map((invoice) => [
            invoice.invoice_no,
            invoice.status,
            invoice.invoice_date,
            invoice.sent_date ?? "",
            invoice.total,
            invoice.open_balance,
          ])}
          title="Invoice Register"
        />
      </section>
    </section>
  );
}

function CustomersView(props: {
  customerActive: boolean;
  customerAddressLine1: string;
  customerAddressLine2: string;
  customerCity: string;
  customerContactName: string;
  customerEmail: string;
  customerName: string;
  customerNotes: string;
  customerPhone: string;
  customerPostalCode: string;
  customerState: string;
  customerTerms: string;
  customers: Customer[];
  onActiveChange: (value: boolean) => void;
  onAddressLine1Change: (value: string) => void;
  onAddressLine2Change: (value: string) => void;
  onCityChange: (value: string) => void;
  onContactNameChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  onNameChange: (value: string) => void;
  onNotesChange: (value: string) => void;
  onPhoneChange: (value: string) => void;
  onPostalCodeChange: (value: string) => void;
  onStateChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onTermsChange: (value: string) => void;
}) {
  return (
    <section className="stacked-panels">
      <form className="panel form-panel" onSubmit={props.onSubmit}>
        <p className="eyebrow">New customer</p>
        <div className="form-grid form-grid-wide">
          <label>
            <span>Name</span>
            <input
              onChange={(event) => props.onNameChange(event.target.value)}
              placeholder="Air Advantage"
              value={props.customerName}
            />
          </label>
          <label>
            <span>Contact Name</span>
            <input
              onChange={(event) => props.onContactNameChange(event.target.value)}
              placeholder="Accounts Payable"
              value={props.customerContactName}
            />
          </label>
          <label>
            <span>Customer email</span>
            <input
              onChange={(event) => props.onEmailChange(event.target.value)}
              placeholder="billing@example.com"
              type="email"
              value={props.customerEmail}
            />
          </label>
          <label>
            <span>Phone</span>
            <input
              onChange={(event) => props.onPhoneChange(event.target.value)}
              placeholder="555-0100"
              value={props.customerPhone}
            />
          </label>
          <label>
            <span>Address line 1</span>
            <input
              onChange={(event) => props.onAddressLine1Change(event.target.value)}
              placeholder="100 Aviation Way"
              value={props.customerAddressLine1}
            />
          </label>
          <label>
            <span>Address line 2</span>
            <input
              onChange={(event) => props.onAddressLine2Change(event.target.value)}
              placeholder="Suite 200"
              value={props.customerAddressLine2}
            />
          </label>
          <label>
            <span>City</span>
            <input
              onChange={(event) => props.onCityChange(event.target.value)}
              placeholder="Tulsa"
              value={props.customerCity}
            />
          </label>
          <label>
            <span>State</span>
            <input
              onChange={(event) => props.onStateChange(event.target.value)}
              placeholder="OK"
              value={props.customerState}
            />
          </label>
          <label>
            <span>Postal code</span>
            <input
              onChange={(event) => props.onPostalCodeChange(event.target.value)}
              placeholder="74101"
              value={props.customerPostalCode}
            />
          </label>
          <label>
            <span>Terms</span>
            <input
              onChange={(event) => props.onTermsChange(event.target.value)}
              placeholder="Due on receipt"
              value={props.customerTerms}
            />
          </label>
        </div>
        <label>
          <span>Notes</span>
          <textarea
            onChange={(event) => props.onNotesChange(event.target.value)}
            placeholder="Customer notes"
            rows={3}
            value={props.customerNotes}
          />
        </label>
        <label className="toggle-row">
          <input
            checked={props.customerActive}
            onChange={(event) => props.onActiveChange(event.target.checked)}
            type="checkbox"
          />
          <span>Active customer</span>
        </label>
        <button className="primary-button" type="submit">
          <Plus aria-hidden="true" size={17} />
          <span>Add Customer</span>
        </button>
      </form>

      <RecordTable
        columns={["Name", "Contact Name", "Customer email", "Phone", "Address", "Terms", "Status", "Notes"]}
        rows={props.customers.map((customer) => [
          customer.name,
          customer.billing_contact_name ?? "",
          customer.billing_email ?? "",
          customer.phone ?? "",
          [
            customer.billing_address_line1,
            customer.billing_address_line2,
            [customer.billing_city, customer.billing_state, customer.billing_postal_code]
              .filter(Boolean)
              .join(" "),
          ]
            .filter(Boolean)
            .join(", "),
          customer.default_terms,
          customer.active ? "Active" : "Inactive",
          customer.notes ?? "",
        ])}
        title="Customer Directory"
      />
    </section>
  );
}

function ProjectsView(props: {
  customerNameById: Map<number, string>;
  customers: Customer[];
  onCustomerChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onFixedFeeChange: (value: string) => void;
  onNameChange: (value: string) => void;
  onProjectNoChange: (value: string) => void;
  onRateChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  projectCustomerId: string;
  projectDescription: string;
  projectFixedFee: string;
  projectName: string;
  projectNo: string;
  projectRate: string;
  projects: Project[];
}) {
  return (
    <section className="stacked-panels">
      <form className="panel form-panel" onSubmit={props.onSubmit}>
        <p className="eyebrow">New project</p>
        <div className="form-grid form-grid-wide">
          <label>
            <span>Customer</span>
            <select
              onChange={(event) => props.onCustomerChange(event.target.value)}
              value={props.projectCustomerId}
            >
              <option value="">Select customer</option>
              {props.customers.map((customer) => (
                <option key={customer.id} value={customer.id}>
                  {customer.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Project number</span>
            <input
              onChange={(event) => props.onProjectNoChange(event.target.value)}
              placeholder="AA-001"
              value={props.projectNo}
            />
          </label>
          <label>
            <span>Project Name</span>
            <input
              onChange={(event) => props.onNameChange(event.target.value)}
              placeholder="Tower Upgrade"
              value={props.projectName}
            />
          </label>
          <label>
            <span>Default hourly rate</span>
            <input
              onChange={(event) => props.onRateChange(event.target.value)}
              placeholder="125.00"
              value={props.projectRate}
            />
          </label>
          <label>
            <span>Fixed fee amount</span>
            <input
              onChange={(event) => props.onFixedFeeChange(event.target.value)}
              placeholder="0.00"
              value={props.projectFixedFee}
            />
          </label>
        </div>
        <label>
          <span>Project Description</span>
          <textarea
            onChange={(event) => props.onDescriptionChange(event.target.value)}
            placeholder="Project scope or billing notes"
            rows={3}
            value={props.projectDescription}
          />
        </label>
        <button className="primary-button" type="submit">
          <Plus aria-hidden="true" size={17} />
          <span>Add Project</span>
        </button>
      </form>

      <RecordTable
        columns={["Project #", "Project Name", "Customer", "Rate", "Fixed fee", "Project Description"]}
        rows={props.projects.map((project) => [
          project.project_no ?? "",
          project.name,
          props.customerNameById.get(project.customer_id) ?? `Customer ${project.customer_id}`,
          project.default_hourly_rate ?? "",
          project.fixed_fee_amount ?? "",
          project.description ?? "",
        ])}
        title="Project Register"
      />
    </section>
  );
}

function TimeEntriesView(props: {
  onBillableChange: (value: boolean) => void;
  onDateChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onHoursChange: (value: string) => void;
  onProjectChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onWorkTypeChange: (value: string) => void;
  projectNameById: Map<number, string>;
  projects: Project[];
  timeBillable: boolean;
  timeCodeOptions: TimeCodeOption[];
  timeDate: string;
  timeDescription: string;
  timeEntries: TimeEntry[];
  timeHours: string;
  timeProjectId: string;
  timeWorkType: string;
}) {
  return (
    <section className="stacked-panels">
      <form className="panel form-panel" onSubmit={props.onSubmit}>
        <p className="eyebrow">New time entry</p>
        <div className="form-grid form-grid-wide">
          <label>
            <span>Project</span>
            <select
              onChange={(event) => props.onProjectChange(event.target.value)}
              value={props.timeProjectId}
            >
              <option value="">Select project</option>
              {props.projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.project_no} · {project.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Date</span>
            <input
              onChange={(event) => props.onDateChange(event.target.value)}
              type="date"
              value={props.timeDate}
            />
          </label>
          <label>
            <span>Time Code</span>
            <select
              onChange={(event) => props.onWorkTypeChange(event.target.value)}
              value={props.timeWorkType}
            >
              <option value="">Select time code</option>
              {props.timeCodeOptions.map((option) => (
                <option key={option.code} value={option.code}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Hours</span>
            <input
              onChange={(event) => props.onHoursChange(event.target.value)}
              placeholder="1.00"
              value={props.timeHours}
            />
          </label>
        </div>
        <label>
          <span>Description</span>
          <textarea
            onChange={(event) => props.onDescriptionChange(event.target.value)}
            placeholder="Field labor"
            rows={3}
            value={props.timeDescription}
          />
        </label>
        <label className="toggle-row">
          <input
            checked={props.timeBillable}
            onChange={(event) => props.onBillableChange(event.target.checked)}
            type="checkbox"
          />
          <span>Billable time</span>
        </label>
        <button className="primary-button" type="submit">
          <Plus aria-hidden="true" size={17} />
          <span>Add Time</span>
        </button>
      </form>

      <RecordTable
        columns={["Date", "Project", "Time Code", "Description", "Hours", "Rate", "Billable", "Status"]}
        rows={props.timeEntries.map((entry) => [
          entry.date,
          props.projectNameById.get(entry.project_id) ?? `Project ${entry.project_id}`,
          entry.work_type ?? "",
          entry.description,
          entry.hours,
          entry.rate,
          entry.billable ? "Yes" : "No",
          entry.billing_status,
        ])}
        title="Time Entries"
      />
    </section>
  );
}

function ExpensesView(props: {
  categoryName: string;
  categoryNameById: Map<number, string>;
  expenseCategories: ExpenseCategory[];
  expenseCategoryId: string;
  expenseDate: string;
  expenseDescription: string;
  expenseProjectId: string;
  expenseQty: string;
  expenseUnitCost: string;
  expenseVendor: string;
  expenses: Expense[];
  onCategoryChange: (value: string) => void;
  onCategoryNameChange: (value: string) => void;
  onCategorySubmit: (event: FormEvent<HTMLFormElement>) => void;
  onDateChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onProjectChange: (value: string) => void;
  onQtyChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onUnitCostChange: (value: string) => void;
  onVendorChange: (value: string) => void;
  projectNameById: Map<number, string>;
  projects: Project[];
}) {
  return (
    <section className="stacked-panels">
      <section className="record-layout">
        <form className="panel form-panel" onSubmit={props.onCategorySubmit}>
          <p className="eyebrow">Expense category</p>
          <label>
            <span>Name</span>
            <input
              onChange={(event) => props.onCategoryNameChange(event.target.value)}
              placeholder="Materials"
              value={props.categoryName}
            />
          </label>
          <button className="primary-button" type="submit">
            <Plus aria-hidden="true" size={17} />
            <span>Add Category</span>
          </button>
        </form>

        <form className="panel form-panel" onSubmit={props.onSubmit}>
          <p className="eyebrow">New expense</p>
          <label>
            <span>Project</span>
            <select
              onChange={(event) => props.onProjectChange(event.target.value)}
              value={props.expenseProjectId}
            >
              <option value="">Select project</option>
              {props.projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </label>
          <div className="form-grid">
            <label>
              <span>Date</span>
              <input
                onChange={(event) => props.onDateChange(event.target.value)}
                type="date"
                value={props.expenseDate}
              />
            </label>
            <label>
              <span>Category</span>
              <select
                onChange={(event) => props.onCategoryChange(event.target.value)}
                value={props.expenseCategoryId}
              >
                <option value="">None</option>
                {props.expenseCategories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label>
            <span>Vendor</span>
            <input
              onChange={(event) => props.onVendorChange(event.target.value)}
              placeholder="Supply House"
              value={props.expenseVendor}
            />
          </label>
          <label>
            <span>Description</span>
            <input
              onChange={(event) => props.onDescriptionChange(event.target.value)}
              placeholder="Cable"
              value={props.expenseDescription}
            />
          </label>
          <div className="form-grid">
            <label>
              <span>Qty</span>
              <input
                onChange={(event) => props.onQtyChange(event.target.value)}
                value={props.expenseQty}
              />
            </label>
            <label>
              <span>Unit cost</span>
              <input
                onChange={(event) => props.onUnitCostChange(event.target.value)}
                value={props.expenseUnitCost}
              />
            </label>
          </div>
          <button className="primary-button" type="submit">
            <Plus aria-hidden="true" size={17} />
            <span>Add Expense</span>
          </button>
        </form>
      </section>

      <RecordTable
        columns={["Date", "Project", "Category", "Description", "Total", "Status"]}
        rows={props.expenses.map((expense) => [
          expense.date,
          props.projectNameById.get(expense.project_id) ?? `Project ${expense.project_id}`,
          expense.category_id ? props.categoryNameById.get(expense.category_id) ?? "" : "",
          expense.description,
          expense.total,
          expense.reimbursement_status,
        ])}
        title="Expenses"
      />
    </section>
  );
}

function RecordTable(props: { columns: string[]; rows: string[][]; title: string }) {
  const gridTemplateColumns = `repeat(${props.columns.length}, minmax(130px, 1fr))`;

  return (
    <section className="panel table-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Records</p>
          <h2>{props.title}</h2>
        </div>
        <span className="panel-note">{props.rows.length} rows</span>
      </div>
      <div className="data-table">
        <div className="data-row header" style={{ gridTemplateColumns }}>
          {props.columns.map((column) => (
            <span key={column}>{column}</span>
          ))}
        </div>
        {props.rows.map((row) => (
          <div className="data-row" key={row.join("|")} style={{ gridTemplateColumns }}>
            {row.map((cell, index) => (
              <span key={`${cell}-${index}`}>{cell || "—"}</span>
            ))}
          </div>
        ))}
        {props.rows.length === 0 ? <p className="empty-copy">No records yet.</p> : null}
      </div>
    </section>
  );
}

function SelectableRecordTable(props: {
  columns: string[];
  rows: Array<{ cells: string[]; key: string; onToggle: () => void; selected: boolean }>;
  title: string;
}) {
  const gridTemplateColumns = `72px repeat(${props.columns.length}, minmax(130px, 1fr))`;

  return (
    <section className="panel table-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Candidates</p>
          <h2>{props.title}</h2>
        </div>
        <span className="panel-note">{props.rows.length} rows</span>
      </div>
      <div className="data-table">
        <div className="data-row header" style={{ gridTemplateColumns }}>
          <span>Invoice?</span>
          {props.columns.map((column) => (
            <span key={column}>{column}</span>
          ))}
        </div>
        {props.rows.map((row) => (
          <div className="data-row" key={row.key} style={{ gridTemplateColumns }}>
            <span className="checkbox-cell">
              <input checked={row.selected} onChange={row.onToggle} type="checkbox" />
            </span>
            {row.cells.map((cell, index) => (
              <span key={`${row.key}-${index}`}>{cell || "—"}</span>
            ))}
          </div>
        ))}
        {props.rows.length === 0 ? <p className="empty-copy">No invoice candidates.</p> : null}
      </div>
    </section>
  );
}

function formatMoney(value: number) {
  return value.toFixed(2);
}

function nextInvoiceNo(current: string) {
  const value = Number(current);
  if (Number.isInteger(value) && Number.isFinite(value)) {
    return String(value + 1);
  }
  return current;
}

type TimeCodeOption = {
  code: string;
  label: string;
  rate: string;
};

function buildTimeCodeOptions(project: Project | undefined): TimeCodeOption[] {
  if (!project) {
    return [];
  }

  const baseRate = Number(project.default_hourly_rate ?? "0");
  const asMoney = (value: number) => value.toFixed(2);

  return [
    { code: "ST", label: `ST-$${asMoney(baseRate)}`, rate: asMoney(baseRate) },
    { code: "OT", label: `OT-$${asMoney(baseRate * 1.5)}`, rate: asMoney(baseRate * 1.5) },
    { code: "TT", label: `TT-$${asMoney(baseRate * 0.5)}`, rate: asMoney(baseRate * 0.5) },
    { code: "HD", label: `HD-$0.00`, rate: "0.00" },
  ];
}
