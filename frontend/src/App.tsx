const proofWorkflow = [
  "Customer + Project",
  "Time + Expense",
  "Invoice Builder",
  "Invoice PDF",
  "Payment Application",
  "Customer Balance",
];

export default function App() {
  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">Windsage Ledger</p>
        <h1>Simple books I can understand.</h1>
        <p className="lede">
          A local-first accounting workspace for project time, reimbursable expenses,
          invoices, payments, advances, and customer balances.
        </p>
      </section>

      <section className="workflow" aria-labelledby="workflow-heading">
        <h2 id="workflow-heading">First Proof Workflow</h2>
        <ol>
          {proofWorkflow.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </section>
    </main>
  );
}
