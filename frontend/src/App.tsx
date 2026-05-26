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
  LayoutDashboard,
  Plus,
  ReceiptText,
  RefreshCw,
  WalletCards,
} from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import {
  createCustomer,
  createExpense,
  createExpenseCategory,
  createProject,
  createTimeEntry,
  getHealth,
  listExpenseCategories,
  listExpenses,
  listCustomers,
  listProjects,
  listTimeEntries,
  type ApiHealth,
  type Customer,
  type Expense,
  type ExpenseCategory,
  type Project,
  type TimeEntry,
} from "./api";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, key: "dashboard" },
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
  dashboard: "Operations Dashboard",
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

const workflowRows = [
  {
    name: "Customer and project setup",
    status: "UI started",
    endpoint: "/api/customers, /api/projects",
  },
  {
    name: "Time and expense capture",
    status: "Backend ready",
    endpoint: "/api/time-entries, /api/expenses",
  },
  {
    name: "Invoice builder",
    status: "Backend ready",
    endpoint: "/api/invoice-builder/candidates",
  },
  {
    name: "Payments and balances",
    status: "Backend ready",
    endpoint: "/api/payments, /api/customers/{id}/balance",
  },
  {
    name: "Reports and backups",
    status: "Backend ready",
    endpoint: "/api/reports/ar-aging, /api/backups",
  },
  {
    name: "Frontend workflows",
    status: "In progress",
    endpoint: "Customers and projects UI",
  },
];

export default function App() {
  const [activeSection, setActiveSection] = useState<SectionKey>("dashboard");
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [timeEntries, setTimeEntries] = useState<TimeEntry[]>([]);
  const [expenseCategories, setExpenseCategories] = useState<ExpenseCategory[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [dataError, setDataError] = useState<string | null>(null);
  const [customerName, setCustomerName] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [projectName, setProjectName] = useState("");
  const [projectCustomerId, setProjectCustomerId] = useState("");
  const [projectRate, setProjectRate] = useState("125.00");
  const [timeProjectId, setTimeProjectId] = useState("");
  const [timeDate, setTimeDate] = useState(new Date().toISOString().slice(0, 10));
  const [timeDescription, setTimeDescription] = useState("");
  const [timeHours, setTimeHours] = useState("1.00");
  const [categoryName, setCategoryName] = useState("");
  const [expenseProjectId, setExpenseProjectId] = useState("");
  const [expenseCategoryId, setExpenseCategoryId] = useState("");
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().slice(0, 10));
  const [expenseDescription, setExpenseDescription] = useState("");
  const [expenseVendor, setExpenseVendor] = useState("");
  const [expenseQty, setExpenseQty] = useState("1.00");
  const [expenseUnitCost, setExpenseUnitCost] = useState("0.00");

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

  const summaryCards = [
    { label: "Customers", value: String(customers.length), detail: "Active master records" },
    { label: "Projects", value: String(projects.length), detail: "Project billing contexts" },
    { label: "Unbilled time", value: String(timeEntries.length), detail: "Source labor rows" },
    { label: "Expenses", value: String(expenses.length), detail: "Reimbursable source rows" },
  ];

  const customerNameById = new Map(customers.map((customer) => [customer.id, customer.name]));
  const projectNameById = new Map(projects.map((project) => [project.id, project.name]));
  const categoryNameById = new Map(
    expenseCategories.map((category) => [category.id, category.name]),
  );

  const submitCustomer = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!customerName.trim()) {
      return;
    }
    try {
      await createCustomer({
        name: customerName.trim(),
        billing_email: customerEmail.trim() || null,
      });
      setCustomerName("");
      setCustomerEmail("");
      await refreshData();
    } catch (error) {
      setDataError(error instanceof Error ? error.message : "Unable to create customer");
    }
  };

  const submitProject = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!projectName.trim() || !projectCustomerId) {
      return;
    }
    try {
      await createProject({
        customer_id: Number(projectCustomerId),
        name: projectName.trim(),
        default_hourly_rate: projectRate.trim() || null,
      });
      setProjectName("");
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
    try {
      await createTimeEntry({
        date: timeDate,
        project_id: Number(timeProjectId),
        description: timeDescription.trim(),
        hours: timeHours,
        billable: true,
      });
      setTimeDescription("");
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

        {activeSection === "dashboard" ? (
          <Dashboard summaryCards={summaryCards} />
        ) : null}

        {activeSection === "customers" ? (
          <CustomersView
            customerEmail={customerEmail}
            customerName={customerName}
            customers={customers}
            onEmailChange={setCustomerEmail}
            onNameChange={setCustomerName}
            onSubmit={submitCustomer}
          />
        ) : null}

        {activeSection === "projects" ? (
          <ProjectsView
            customerNameById={customerNameById}
            customers={customers}
            onCustomerChange={setProjectCustomerId}
            onNameChange={setProjectName}
            onRateChange={setProjectRate}
            onSubmit={submitProject}
            projectCustomerId={projectCustomerId}
            projectName={projectName}
            projectRate={projectRate}
            projects={projects}
          />
        ) : null}

        {activeSection === "time" ? (
          <TimeEntriesView
            onDateChange={setTimeDate}
            onDescriptionChange={setTimeDescription}
            onHoursChange={setTimeHours}
            onProjectChange={setTimeProjectId}
            onSubmit={submitTimeEntry}
            projectNameById={projectNameById}
            projects={projects}
            timeDate={timeDate}
            timeDescription={timeDescription}
            timeEntries={timeEntries}
            timeHours={timeHours}
            timeProjectId={timeProjectId}
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

        {!["dashboard", "customers", "projects", "time", "expenses"].includes(activeSection) ? (
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

function Dashboard({ summaryCards }: { summaryCards: Array<{ label: string; value: string; detail: string }> }) {
  return (
    <>
      <section className="summary-grid" aria-label="Project status summary">
        {summaryCards.map((card) => (
          <article className="summary-card" key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            <p>{card.detail}</p>
          </article>
        ))}
      </section>

      <section className="panel" aria-labelledby="workflow-heading">
        <div className="panel-header">
          <div>
            <p className="eyebrow">First proof workflow</p>
            <h2 id="workflow-heading">Implementation Status</h2>
          </div>
          <span className="panel-note">Now: customers and projects UI</span>
        </div>

        <div className="workflow-table" role="table" aria-label="Workflow status">
          <div className="workflow-row header" role="row">
            <span role="columnheader">Workflow area</span>
            <span role="columnheader">Status</span>
            <span role="columnheader">API surface</span>
          </div>
          {workflowRows.map((row) => (
            <div className="workflow-row" role="row" key={row.name}>
              <span role="cell">{row.name}</span>
              <span role="cell">
                <mark>{row.status}</mark>
              </span>
              <code role="cell">{row.endpoint}</code>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function CustomersView(props: {
  customerEmail: string;
  customerName: string;
  customers: Customer[];
  onEmailChange: (value: string) => void;
  onNameChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <section className="record-layout">
      <form className="panel form-panel" onSubmit={props.onSubmit}>
        <p className="eyebrow">New customer</p>
        <label>
          <span>Name</span>
          <input
            onChange={(event) => props.onNameChange(event.target.value)}
            placeholder="Air Advantage"
            value={props.customerName}
          />
        </label>
        <label>
          <span>Billing email</span>
          <input
            onChange={(event) => props.onEmailChange(event.target.value)}
            placeholder="billing@example.com"
            type="email"
            value={props.customerEmail}
          />
        </label>
        <button className="primary-button" type="submit">
          <Plus aria-hidden="true" size={17} />
          <span>Add Customer</span>
        </button>
      </form>

      <RecordTable
        columns={["Name", "Email", "Terms", "Status"]}
        rows={props.customers.map((customer) => [
          customer.name,
          customer.billing_email ?? "",
          customer.default_terms,
          customer.active ? "Active" : "Inactive",
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
  onNameChange: (value: string) => void;
  onRateChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  projectCustomerId: string;
  projectName: string;
  projectRate: string;
  projects: Project[];
}) {
  return (
    <section className="record-layout">
      <form className="panel form-panel" onSubmit={props.onSubmit}>
        <p className="eyebrow">New project</p>
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
          <span>Project name</span>
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
        <button className="primary-button" type="submit">
          <Plus aria-hidden="true" size={17} />
          <span>Add Project</span>
        </button>
      </form>

      <RecordTable
        columns={["Project", "Customer", "Rate", "Status"]}
        rows={props.projects.map((project) => [
          project.name,
          props.customerNameById.get(project.customer_id) ?? `Customer ${project.customer_id}`,
          project.default_hourly_rate ?? "",
          project.status,
        ])}
        title="Project Register"
      />
    </section>
  );
}

function TimeEntriesView(props: {
  onDateChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onHoursChange: (value: string) => void;
  onProjectChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  projectNameById: Map<number, string>;
  projects: Project[];
  timeDate: string;
  timeDescription: string;
  timeEntries: TimeEntry[];
  timeHours: string;
  timeProjectId: string;
}) {
  return (
    <section className="record-layout">
      <form className="panel form-panel" onSubmit={props.onSubmit}>
        <p className="eyebrow">New time entry</p>
        <label>
          <span>Project</span>
          <select
            onChange={(event) => props.onProjectChange(event.target.value)}
            value={props.timeProjectId}
          >
            <option value="">Select project</option>
            {props.projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
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
          <span>Description</span>
          <input
            onChange={(event) => props.onDescriptionChange(event.target.value)}
            placeholder="Field labor"
            value={props.timeDescription}
          />
        </label>
        <label>
          <span>Hours</span>
          <input
            onChange={(event) => props.onHoursChange(event.target.value)}
            placeholder="1.00"
            value={props.timeHours}
          />
        </label>
        <button className="primary-button" type="submit">
          <Plus aria-hidden="true" size={17} />
          <span>Add Time</span>
        </button>
      </form>

      <RecordTable
        columns={["Date", "Project", "Description", "Hours", "Status"]}
        rows={props.timeEntries.map((entry) => [
          entry.date,
          props.projectNameById.get(entry.project_id) ?? `Project ${entry.project_id}`,
          entry.description,
          entry.hours,
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
