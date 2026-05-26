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
  createProject,
  getHealth,
  listCustomers,
  listProjects,
  type ApiHealth,
  type Customer,
  type Project,
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
  const [dataError, setDataError] = useState<string | null>(null);
  const [customerName, setCustomerName] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [projectName, setProjectName] = useState("");
  const [projectCustomerId, setProjectCustomerId] = useState("");
  const [projectRate, setProjectRate] = useState("125.00");

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
      const [customerRows, projectRows] = await Promise.all([listCustomers(), listProjects()]);
      setCustomers(customerRows);
      setProjects(projectRows);
      setDataError(null);
      if (!projectCustomerId && customerRows[0]) {
        setProjectCustomerId(String(customerRows[0].id));
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
    { label: "Backend tests", value: "30", detail: "Passing workflow checks" },
    { label: "Proof target", value: "662", detail: "Invoice validation path" },
  ];

  const customerNameById = new Map(customers.map((customer) => [customer.id, customer.name]));

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

        {!["dashboard", "customers", "projects"].includes(activeSection) ? (
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

function RecordTable(props: { columns: string[]; rows: string[][]; title: string }) {
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
        <div className="data-row header">
          {props.columns.map((column) => (
            <span key={column}>{column}</span>
          ))}
        </div>
        {props.rows.map((row) => (
          <div className="data-row" key={row.join("|")}>
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
