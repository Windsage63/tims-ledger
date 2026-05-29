export type ApiHealth = {
  status: string;
  app: string;
};

export type Customer = {
  id: number;
  name: string;
  billing_contact_name: string | null;
  billing_email: string | null;
  phone: string | null;
  billing_address_line1: string | null;
  billing_address_line2: string | null;
  billing_city: string | null;
  billing_state: string | null;
  billing_postal_code: string | null;
  default_terms: string;
  active: boolean;
  notes: string | null;
};

export type Project = {
  id: number;
  project_no: string | null;
  customer_id: number;
  name: string;
  description: string | null;
  contract_type: "time_and_materials" | "fixed_fee" | "hourly";
  status: "active" | "completed" | "inactive";
  default_hourly_rate: string | null;
  fixed_fee_amount: string | null;
};

export type ExpenseCategory = {
  id: number;
  name: string;
  default_billable: boolean;
  default_reimbursable: boolean;
};

export type TimeEntry = {
  id: number;
  date: string;
  project_id: number;
  customer_id: number;
  description: string;
  hours: string;
  work_type: string | null;
  rate: string;
  billable: boolean;
  billing_status:
    | "unbilled"
    | "assigned"
    | "drafted"
    | "invoiced"
    | "voided"
    | "non_billable";
  invoice_id: number | null;
};

export type Expense = {
  id: number;
  date: string;
  project_id: number;
  customer_id: number;
  vendor: string | null;
  description: string;
  qty: string;
  unit_cost: string;
  total: string;
  category_id: number | null;
  billable: boolean;
  reimbursable: boolean;
  reimbursement_status:
    | "unbilled"
    | "assigned"
    | "drafted"
    | "invoiced"
    | "voided"
    | "non_billable";
  invoice_id: number | null;
};

export type InvoiceLine = {
  id: number;
  invoice_id: number;
  source_type: string | null;
  source_id: number | null;
  description: string;
  qty: string;
  unit_price: string;
  amount: string;
  line_group: string | null;
  sort_order: number;
};

export type Invoice = {
  id: number;
  invoice_no: string;
  customer_id: number;
  invoice_date: string;
  sent_date: string | null;
  due_date: string | null;
  status: "draft" | "issued" | "sent" | "partially_paid" | "paid" | "overdue" | "void";
  terms: string;
  subtotal_labor: string;
  subtotal_expenses: string;
  freight: string;
  per_diem: string;
  other: string;
  sales_tax: string;
  total: string;
  open_balance: string;
  created_at: string;
  updated_at: string;
};

export type InvoiceDetail = Invoice & {
  lines: InvoiceLine[];
};

export type InvoiceCandidates = {
  customer_id: number;
  project_id: number | null;
  time_entries: TimeEntry[];
  expenses: Expense[];
};

export type CustomerCreate = {
  name: string;
  billing_contact_name?: string | null;
  billing_email?: string | null;
  phone?: string | null;
  billing_address_line1?: string | null;
  billing_address_line2?: string | null;
  billing_city?: string | null;
  billing_state?: string | null;
  billing_postal_code?: string | null;
  default_terms?: string;
  active?: boolean;
  notes?: string | null;
};

export type ProjectCreate = {
  customer_id: number;
  name: string;
  project_no: string;
  description?: string | null;
  contract_type?: Project["contract_type"];
  status?: Project["status"];
  default_hourly_rate?: string | null;
  fixed_fee_amount?: string | null;
};

export type TimeEntryCreate = {
  date: string;
  project_id: number;
  description: string;
  hours: string;
  work_type?: string | null;
  rate?: string | null;
  billable?: boolean;
};

export type ExpenseCategoryCreate = {
  name: string;
  default_billable?: boolean;
  default_reimbursable?: boolean;
};

export type ExpenseCreate = {
  date: string;
  project_id: number;
  vendor?: string | null;
  description: string;
  qty: string;
  unit_cost: string;
  category_id?: number | null;
  billable?: boolean;
  reimbursable?: boolean;
};

export type InvoiceCreate = {
  invoice_no: string;
  customer_id: number;
  invoice_date: string;
  time_entry_ids?: number[];
  expense_ids?: number[];
  due_date?: string | null;
  terms?: string;
};

export type InvoiceIssue = {
  sent_date: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8004";

export async function getHealth(): Promise<ApiHealth> {
  return apiRequest<ApiHealth>("/health");
}

export async function listCustomers(): Promise<Customer[]> {
  return apiRequest<Customer[]>("/api/customers");
}

export async function createCustomer(payload: CustomerCreate): Promise<Customer> {
  return apiRequest<Customer>("/api/customers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listProjects(): Promise<Project[]> {
  return apiRequest<Project[]>("/api/projects");
}

export async function createProject(payload: ProjectCreate): Promise<Project> {
  return apiRequest<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listTimeEntries(): Promise<TimeEntry[]> {
  return apiRequest<TimeEntry[]>("/api/time-entries");
}

export async function createTimeEntry(payload: TimeEntryCreate): Promise<TimeEntry> {
  return apiRequest<TimeEntry>("/api/time-entries", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listExpenseCategories(): Promise<ExpenseCategory[]> {
  return apiRequest<ExpenseCategory[]>("/api/expense-categories");
}

export async function createExpenseCategory(
  payload: ExpenseCategoryCreate,
): Promise<ExpenseCategory> {
  return apiRequest<ExpenseCategory>("/api/expense-categories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listExpenses(): Promise<Expense[]> {
  return apiRequest<Expense[]>("/api/expenses");
}

export async function createExpense(payload: ExpenseCreate): Promise<Expense> {
  return apiRequest<Expense>("/api/expenses", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getInvoiceCandidates(params: {
  customer_id: number;
  project_id?: number;
}): Promise<InvoiceCandidates> {
  const search = new URLSearchParams({ customer_id: String(params.customer_id) });
  if (params.project_id !== undefined) {
    search.set("project_id", String(params.project_id));
  }
  return apiRequest<InvoiceCandidates>(`/api/invoice-builder/candidates?${search.toString()}`);
}

export async function listInvoices(params: {
  customer_id?: number;
  status?: Invoice["status"];
} = {}): Promise<Invoice[]> {
  const search = new URLSearchParams();
  if (params.customer_id !== undefined) {
    search.set("customer_id", String(params.customer_id));
  }
  if (params.status !== undefined) {
    search.set("status", params.status);
  }
  const suffix = search.size > 0 ? `?${search.toString()}` : "";
  return apiRequest<Invoice[]>(`/api/invoices${suffix}`);
}

export async function getInvoice(invoiceId: number): Promise<InvoiceDetail> {
  return apiRequest<InvoiceDetail>(`/api/invoices/${invoiceId}`);
}

export async function createInvoice(payload: InvoiceCreate): Promise<InvoiceDetail> {
  return apiRequest<InvoiceDetail>("/api/invoices", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function issueInvoice(
  invoiceId: number,
  payload: InvoiceIssue,
): Promise<InvoiceDetail> {
  return apiRequest<InvoiceDetail>(`/api/invoices/${invoiceId}/issue`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}
