export type ApiHealth = {
  status: string;
  app: string;
};

export type Customer = {
  id: number;
  name: string;
  billing_email: string | null;
  phone: string | null;
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
  billing_status: "unbilled" | "drafted" | "invoiced" | "voided" | "non_billable";
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
  reimbursement_status: "unbilled" | "drafted" | "invoiced" | "voided" | "non_billable";
  invoice_id: number | null;
};

export type CustomerCreate = {
  name: string;
  billing_email?: string | null;
  phone?: string | null;
  default_terms?: string;
  notes?: string | null;
};

export type ProjectCreate = {
  customer_id: number;
  name: string;
  project_no?: string | null;
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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

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
