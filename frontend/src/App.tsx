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
  ReceiptText,
  WalletCards,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { getHealth, type ApiHealth } from "./api";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, active: true },
  { label: "Customers", icon: Building2 },
  { label: "Projects", icon: BriefcaseBusiness },
  { label: "Time", icon: Clock3 },
  { label: "Expenses", icon: ReceiptText },
  { label: "Invoices", icon: FileText },
  { label: "Payments", icon: WalletCards },
  { label: "Reports", icon: BadgeDollarSign },
  { label: "Imports", icon: FileInput },
  { label: "Backups", icon: DatabaseBackup },
];

const workflowRows = [
  {
    name: "Customer and project setup",
    status: "Backend ready",
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
    status: "Next",
    endpoint: "Customers and projects UI",
  },
];

const summaryCards = [
  { label: "Backend API groups", value: "12", detail: "Core accounting routes" },
  { label: "Backend tests", value: "30", detail: "Passing workflow checks" },
  { label: "Current focus", value: "UI", detail: "Operational app shell" },
  { label: "Proof target", value: "662", detail: "Invoice validation path" },
];

export default function App() {
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

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

  const apiStatus = useMemo(() => {
    if (health) {
      return { label: "Connected", tone: "online" };
    }
    if (healthError) {
      return { label: "Offline", tone: "offline" };
    }
    return { label: "Checking", tone: "pending" };
  }, [health, healthError]);

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
                className={item.active ? "nav-item active" : "nav-item"}
                key={item.label}
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
            <h1>Operations Dashboard</h1>
          </div>
          <div className={`api-status ${apiStatus.tone}`}>
            <Activity aria-hidden="true" size={18} />
            <span>{apiStatus.label}</span>
          </div>
        </header>

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
              <h2 id="workflow-heading">Backend Foundation</h2>
            </div>
            <span className="panel-note">Next: customers and projects UI</span>
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

        <section className="panel two-column" aria-label="Accounting focus">
          <div>
            <p className="eyebrow">Current build path</p>
            <h2>Proof Workflow</h2>
            <p>
              The next UI work turns the tested backend routes into usable screens for the
              customer, project, time, expense, invoice, payment, and balance flow.
            </p>
          </div>
          <div className="checklist">
            <span>Customer + Project</span>
            <span>Time + Expense</span>
            <span>Invoice Builder</span>
            <span>Payment Application</span>
            <span>Customer Balance</span>
          </div>
        </section>
      </main>
    </div>
  );
}
