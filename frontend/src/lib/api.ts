export type Json = Record<string, unknown> | unknown[] | string | number | boolean | null;

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';
const ACCESS_KEY = 'erp_access_token';

let csrfToken = '';
let refreshing = false;
let refreshPromise: Promise<boolean> | null = null;

function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY);
}

function setAccessToken(token: string | null) {
  if (token) localStorage.setItem(ACCESS_KEY, token);
  else localStorage.removeItem(ACCESS_KEY);
}

async function parseResponse(response: Response) {
  if (response.status === 204) return null;
  const text = await response.text();
  if (!text) return null;
  try { return JSON.parse(text) as Json; } catch { return text; }
}

async function getCsrfToken() {
  const response = await fetch(`${API_BASE}/auth/csrf/`, { credentials: 'include', headers: { Accept: 'application/json' } });
  const data = (await parseResponse(response)) as { csrf_token?: string } | null;
  if (!response.ok || !data?.csrf_token) throw new Error('Unable to initialize CSRF protection.');
  csrfToken = data.csrf_token;
  return csrfToken;
}

async function refreshAccessToken() {
  if (refreshing && refreshPromise) return refreshPromise;
  refreshing = true;
  refreshPromise = (async () => {
    try {
      if (!csrfToken) await getCsrfToken();
      const response = await fetch(`${API_BASE}/auth/refresh/`, { method: 'POST', credentials: 'include', headers: { Accept: 'application/json', 'X-CSRFToken': csrfToken } });
      const data = (await parseResponse(response)) as { access?: string } | null;
      if (!response.ok || !data?.access) { setAccessToken(null); return false; }
      setAccessToken(data.access);
      return true;
    } catch { setAccessToken(null); return false; }
    finally { refreshing = false; refreshPromise = null; }
  })();
  return refreshPromise;
}

async function request<T = Json>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const method = (init.method || 'GET').toUpperCase();
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  const token = getAccessToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
    if (!csrfToken) await getCsrfToken();
    headers.set('X-CSRFToken', csrfToken);
    if (!(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  }
  const response = await fetch(`${API_BASE}${path}`, { ...init, credentials: 'include', headers });
  if (response.status === 401 && retry && path !== '/auth/refresh/' && path !== '/auth/login/') {
    const refreshed = await refreshAccessToken();
    if (refreshed) return request<T>(path, init, false);
  }
  const data = await parseResponse(response);
  if (!response.ok) {
    const message = typeof data === 'object' && data !== null && 'detail' in data ? String((data as Record<string, unknown>).detail) : `Request failed with status ${response.status}`;
    throw new Error(message);
  }
  return data as T;
}

async function jsonRequest<T = Json>(path: string, method: string, body?: unknown) {
  return request<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
}

export const api = {
  auth: {
    csrf: getCsrfToken,
    login: async (identifier: string, password: string) => { await getCsrfToken(); const data = await jsonRequest<{ access: string }>('/auth/login/', 'POST', { identifier, password }); setAccessToken(data.access); return data; },
    me: () => request<UserProfile>('/auth/me/'),
    refresh: refreshAccessToken,
    logout: () => jsonRequest('/auth/logout/', 'POST').finally(() => setAccessToken(null)),
    logoutAll: () => jsonRequest('/auth/logout-all/', 'POST').finally(() => setAccessToken(null)),
  },

  organization: {
    company: () => request('/organization/company/'),
    updateCompany: (body: Json) => jsonRequest('/organization/company/', 'PATCH', body),
    sites: (query = '') => request<Paginated>(`/organization/sites/${query}`),
    departments: (query = '') => request<Paginated>(`/organization/departments/${query}`),
    createSite: (body: Json) => jsonRequest('/organization/sites/', 'POST', body),
    updateSite: (id: number, body: Json) => jsonRequest(`/organization/sites/${id}/`, 'PATCH', body),
    deleteSite: (id: number) => request(`/organization/sites/${id}/`, { method: 'DELETE' }),
    createDepartment: (body: Json) => jsonRequest('/organization/departments/', 'POST', body),
    updateDepartment: (id: number, body: Json) => jsonRequest(`/organization/departments/${id}/`, 'PATCH', body),
    deleteDepartment: (id: number) => request(`/organization/departments/${id}/`, { method: 'DELETE' }),
  },

  products: {
    list: (query = '') => request<Paginated>(`/products/${query}`),
    get: (id: number) => request(`/products/${id}/`),
    create: (body: Json) => jsonRequest('/products/', 'POST', body),
    update: (id: number, body: Json) => jsonRequest(`/products/${id}/`, 'PATCH', body),
    delete: (id: number) => request(`/products/${id}/`, { method: 'DELETE' }),
    cartonPricings: (query = '') => request<Paginated>(`/carton-pricings/${query}`),
    createCartonPricing: (body: Json) => jsonRequest('/carton-pricings/', 'POST', body),
    updateCartonPricing: (id: number, body: Json) => jsonRequest(`/carton-pricings/${id}/`, 'PATCH', body),
    deleteCartonPricing: (id: number) => request(`/carton-pricings/${id}/`, { method: 'DELETE' }),
  },

  customers: {
    list: (query = '') => request<Paginated>(`/customers/${query}`),
    get: (id: number) => request(`/customers/${id}/`),
    create: (body: Json) => jsonRequest('/customers/', 'POST', body),
    update: (id: number, body: Json) => jsonRequest(`/customers/${id}/`, 'PATCH', body),
    delete: (id: number) => request(`/customers/${id}/`, { method: 'DELETE' }),
  },

  suppliers: {
    list: (query = '') => request<Paginated>(`/suppliers/${query}`),
    get: (id: number) => request(`/suppliers/${id}/`),
    create: (body: Json) => jsonRequest('/suppliers/', 'POST', body),
    update: (id: number, body: Json) => jsonRequest(`/suppliers/${id}/`, 'PATCH', body),
  },

  coupons: {
    list: (query = '') => request<Paginated>(`/coupons/${query}`),
    get: (id: number) => request(`/coupons/${id}/`),
    create: (body: Json) => jsonRequest('/coupons/', 'POST', body),
    update: (id: number, body: Json) => jsonRequest(`/coupons/${id}/`, 'PATCH', body),
    delete: (id: number) => request(`/coupons/${id}/`, { method: 'DELETE' }),
  },

  employees: {
    list: (query = '') => request<Paginated>(`/employees/${query}`),
    get: (id: number) => request(`/employees/${id}/`),
    options: (query = '') => request<Paginated>(`/employees/options/${query}`),
    create: (body: Json) => jsonRequest('/employees/', 'POST', body),
    update: (id: number, body: Json) => jsonRequest(`/employees/${id}/`, 'PATCH', body),
    delete: (id: number) => request(`/employees/${id}/`, { method: 'DELETE' }),
  },

  invoices: {
    list: (query = '') => request<Paginated>(`/invoices/${query}`),
    get: (id: number) => request(`/invoices/${id}/`),
    create: (body: Json) => jsonRequest('/invoices/', 'POST', body),
    update: (id: number, body: Json) => jsonRequest(`/invoices/${id}/`, 'PATCH', body),
    delete: (id: number) => request(`/invoices/${id}/`, { method: 'DELETE' }),
    confirm: (id: number) => request(`/invoices/${id}/confirm/`, { method: 'POST' }),
    cancel: (id: number) => request(`/invoices/${id}/cancel/`, { method: 'POST' }),
    applyCoupon: (id: number, code: string) => jsonRequest(`/invoices/${id}/apply-coupon/`, 'POST', { code }),
    removeCoupon: (id: number) => jsonRequest(`/invoices/${id}/remove-coupon/`, 'POST'),
    returns: (id: number, body: Json) => jsonRequest(`/invoices/${id}/returns/`, 'POST', body),
  },

  purchases: {
    list: (query = '') => request<Paginated>(`/purchases/${query}`),
    get: (id: number) => request(`/purchases/${id}/`),
    create: (body: Json) => jsonRequest('/purchases/', 'POST', body),
    update: (id: number, body: Json) => jsonRequest(`/purchases/${id}/edit/`, 'PATCH', body),
    confirm: (id: number) => request(`/purchases/${id}/confirm/`, { method: 'POST' }),
    cancel: (id: number) => request(`/purchases/${id}/cancel/`, { method: 'POST' }),
    delete: (id: number) => request(`/purchases/${id}/delete/`, { method: 'DELETE' }),
    returns: (id: number, body: Json) => jsonRequest(`/purchases/${id}/returns/`, 'POST', body),
    supplierPayment: (body: Json) => jsonRequest('/purchases/supplier-payments/', 'POST', body),
  },

  payments: {
    collections: (body: Json) => jsonRequest('/payments/collections/', 'POST', body),
    refunds: (body: Json) => jsonRequest('/payments/refunds/', 'POST', body),
    transactions: (query = '') => request<Paginated>(`/payments/transactions/${query}`),
  },

  inventory: {
    locations: (query = '') => request<Paginated>(`/inventory/locations/${query}`),
    stock: (query = '') => request<Paginated>(`/inventory/stock/${query}`),
    movements: (query = '') => request<Paginated>(`/inventory/movements/${query}`),
    transfer: (body: Json) => jsonRequest('/inventory/transfers/', 'POST', body),
  },

  accounting: {
    dashboardOverview: (query = '') => request<DashboardOverview>(`/accounting/analytics/overview/${query}`),
    accounts: (query = '') => request<Paginated>(`/accounting/accounts/${query}`),
    createAccount: (body: Json) => jsonRequest('/accounting/accounts/', 'POST', body),
    updateAccount: (id: number, body: Json) => jsonRequest(`/accounting/accounts/${id}/`, 'PATCH', body),
    deleteAccount: (id: number) => request(`/accounting/accounts/${id}/`, { method: 'DELETE' }),
    journalEntries: (query = '') => request<Paginated>(`/accounting/journal-entries/${query}`),
    journalEntry: (id: number) => request(`/accounting/journal-entries/${id}/`),
    createJournalEntry: (body: Json) => jsonRequest('/accounting/journal-entries/', 'POST', body),
    postJournalEntry: (id: number) => request(`/accounting/journal-entries/${id}/post/`, { method: 'POST' }),
    expenses: (query = '') => request<Paginated>(`/accounting/expenses/${query}`),
    createExpense: (body: Json) => jsonRequest('/accounting/expenses/', 'POST', body),
    periods: (query = '') => request<Paginated>(`/accounting/periods/${query}`),
    createPeriod: (body: Json) => jsonRequest('/accounting/periods/', 'POST', body),
    closePeriod: (id: number) => request(`/accounting/periods/${id}/close/`, { method: 'POST' }),
    generalLedger: (query = '') => request(`/accounting/general-ledger/${query}`),
    trialBalance: (query = '') => request(`/accounting/trial-balance/${query}`),
    openingBalance: (body: Json) => jsonRequest('/accounting/opening-balance/', 'POST', body),
    profitAndLoss: (query = '') => request(`/accounting/statements/profit-and-loss/${query}`),
    balanceSheet: (query = '') => request(`/accounting/statements/balance-sheet/${query}`),
    cashFlow: (query = '') => request(`/accounting/statements/cash-flow/${query}`),
    customerBalances: (query = '') => request(`/accounting/reports/customer-balances/${query}`),
    supplierBalances: (query = '') => request(`/accounting/reports/supplier-balances/${query}`),
    customerAging: (query = '') => request(`/accounting/reports/customer-aging/${query}`),
    supplierAging: (query = '') => request(`/accounting/reports/supplier-aging/${query}`),
    salesAnalytics: (query = '') => request(`/accounting/analytics/sales/${query}`),
    purchaseAnalytics: (query = '') => request(`/accounting/analytics/purchases/${query}`),
    inventoryAnalytics: (query = '') => request(`/accounting/analytics/inventory/${query}`),
    topProducts: (query = '') => request(`/accounting/analytics/top-products/${query}`),
    salesByEmployee: (query = '') => request(`/accounting/analytics/sales-by-employee/${query}`),
  },
};

export type Paginated = { count: number; next: string | null; previous: string | null; results: Record<string, unknown>[] };
export type UserProfile = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  is_superuser: boolean;
  role_level: number;
  permissions: string[];
};
export type DashboardOverview = {
  sales: { gross_sales: number | string; units_sold: number; invoice_count: number; trend: { date: string; value: number | string }[] };
  purchases: { purchase_value: number | string; units_purchased: number; purchase_count: number; trend: { date: string; value: number | string }[] };
  inventory: { total_units: number; inventory_value: number | string; product_count: number; low_stock_count: number; low_stock_threshold: number; low_stock: { product_id: number; product_name: string; stock: number }[] };
  pnl: { total_revenue: number | string; total_expenses: number | string; net_income: number | string };
  cash_flow: { opening_cash: number | string; total_inflows: number | string; total_outflows: number | string; net_change: number | string; ending_cash: number | string };
  top_products: { product_id: number; 'product__name': string; quantity: number; revenue: number | string }[];
  sales_by_employee: { invoice__created_by_id: number; invoice__created_by__email: string; invoice__created_by__first_name: string; invoice__created_by__last_name: string; employee_name: string; quantity: number; revenue: number | string }[];
  customer_balances: { customer_id: number; customer_name: string; balance: number | string }[];
  supplier_balances: { supplier_id: number; supplier_name: string; balance: number | string }[];
};

export function query(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => { if (value !== undefined && value !== '') search.set(key, String(value)); });
  const value = search.toString();
  return value ? `?${value}` : '';
}