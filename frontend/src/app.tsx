import type { ErrorInfo, ReactNode } from 'react';
import { Component, useEffect, useRef, useState } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { Button, Card, Center, Stack, Text, Loader } from '@mantine/core';

import { PermissionGuard, can } from './components/PermissionGuard';
import { Shell } from './components/Shell';
import { api, type UserProfile } from './lib/api';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from './pages/LoginPage';
import { ProductsPage, CustomersPage, SuppliersPage, EmployeesPage } from './pages/MasterDataPages';
import { CartonPricingPage, CouponsPage } from './pages/CommercialPages';
import { SalesPage, InvoiceDetailsPage, PurchaseDetailsPage, PaymentDetailsPage, PurchasesPage, PaymentsPage, InventoryPage } from './pages/OperationsPages';
import { InventoryLocationsPage, InventoryMovementsPage, InventoryTransferPage } from './pages/InventoryPages';
import { CreateInvoicePage, CreatePurchasePage, CollectPaymentPage, SupplierPaymentPage } from './pages/TransactionPages';
import { AccountingHomePage, AccountsPage, JournalsPage, StatementsPage } from './pages/AccountingPages';
import { BalancesPage, OpeningBalancePage, ManualJournalPage } from './pages/AccountingReportsPages';
import { ExpensesPage, PeriodsPage, GeneralLedgerPage, TrialBalancePage } from './pages/AccountingOperationsPages';
import { CompanyPage, SitesPage, DepartmentsPage } from './pages/OrganizationPages';
import { ShiftPage } from './pages/ShiftPage';

const AUTH_EXPIRED_EVENT = 'erp-auth-expired';
const AUTH_CONTEXT_CHANGED_EVENT = 'erp-context-changed';

class AppErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) { return { error }; }

  componentDidCatch(error: Error, info: ErrorInfo) { console.error('ERP frontend error', error, info); }

  render() {
    if (!this.state.error) return this.props.children;
    return <Center mih="100vh" p="xl"><Card className="glass" radius="xl" withBorder p="xl" maw={620}><Stack gap="sm"><Text size="sm" fw={800} c="red.5" tt="uppercase" lts=".08em">Application error</Text><Text size="xl" fw={800}>Something went wrong in this screen.</Text><Text c="dimmed">The page crashed instead of leaving a blank screen. Reload it and, if it repeats, the message below identifies the runtime error.</Text>{import.meta.env.DEV && <Text size="sm" ff="monospace" c="dimmed">{this.state.error.message}</Text>}<Button onClick={() => window.location.reload()}>Reload workspace</Button></Stack></Card></Center>;
  }
}

function Authenticated({ user, children }: { user: UserProfile; children: ReactNode }) { return <Shell user={user}>{children}</Shell>; }
function ProtectedPage({ user, permission, children }: { user: UserProfile; permission: string; children: ReactNode }) { return <PermissionGuard user={user} permission={permission}>{children}</PermissionGuard>; }
function NotFound() { return <Center h="60vh"><div><h2>Page not found</h2><p>This route is not part of the current ERP workspace.</p></div></Center>; }

function defaultPath(user: UserProfile) {
  if (can(user, 'accounting.view_financial_reports')) return '/';
  if (can(user, 'invoices.view_invoice')) return '/sales';
  if (can(user, 'inventory.view_stockbalance')) return '/inventory';
  if (can(user, 'accounts.start_employee_shift')) return '/shift';
  return '/login';
}

export function App() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();
  const authCheckStarted = useRef(false);

  useEffect(() => {
    const handleAuthExpired = () => { authCheckStarted.current = false; setUser(null); setLoading(false); if (window.location.pathname !== '/login') navigate('/login', { replace: true }); };
    const reloadContext = () => {
      authCheckStarted.current = false;
      setLoading(true);
      api.auth.me().then(setUser).catch(() => { setUser(null); navigate('/login', { replace: true }); }).finally(() => setLoading(false));
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    window.addEventListener(AUTH_CONTEXT_CHANGED_EVENT, reloadContext);
    return () => { window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired); window.removeEventListener(AUTH_CONTEXT_CHANGED_EVENT, reloadContext); };
  }, [navigate]);

  useEffect(() => {
    if (location.pathname === '/login') { authCheckStarted.current = false; setLoading(false); return; }
    if (user || authCheckStarted.current) return;
    authCheckStarted.current = true;
    setLoading(true);
    api.auth.me().then(setUser).catch(() => { setUser(null); navigate('/login', { replace: true }); }).finally(() => setLoading(false));
  }, [location.pathname, navigate, user]);

  if (loading) return <Center h="100vh"><Loader size="lg" /></Center>;
  if (!user && location.pathname !== '/login') return null;
  if (location.pathname === '/login') return user ? <Navigate to={defaultPath(user)} replace /> : <LoginPage />;
  if (location.pathname === '/' && !can(user!, 'accounting.view_financial_reports')) return <Navigate to={defaultPath(user!)} replace />;

  const securedRoutes = [
    { path: '/', permission: 'accounting.view_financial_reports', element: <DashboardPage /> },
    { path: '/shift', permission: 'accounts.start_employee_shift', element: <ShiftPage user={user!} /> },
    { path: '/sales', permission: 'invoices.view_invoice', element: <SalesPage /> },
    { path: '/sales/:id', permission: 'invoices.view_invoice', element: <InvoiceDetailsPage /> },
    { path: '/sales/new', permission: 'invoices.add_invoice', element: <CreateInvoicePage user={user!} /> },
    { path: '/purchases', permission: 'purchases.view_purchase', element: <PurchasesPage /> },
    { path: '/purchases/:id', permission: 'purchases.view_purchase', element: <PurchaseDetailsPage /> },
    { path: '/purchases/new', permission: 'purchases.add_purchase', element: <CreatePurchasePage user={user!} /> },
    { path: '/products', permission: 'products.view_product', element: <ProductsPage /> },
    { path: '/products/cartons', permission: 'products.view_cartonpricing', element: <CartonPricingPage /> },
    { path: '/customers', permission: 'customers.view_customer', element: <CustomersPage /> },
    { path: '/suppliers', permission: 'suppliers.view_supplier', element: <SuppliersPage /> },
    { path: '/employees', permission: 'accounts.view_employee', element: <EmployeesPage /> },
    { path: '/organization/company', permission: 'organization.view_company', element: <CompanyPage /> },
    { path: '/organization/sites', permission: 'organization.view_site', element: <SitesPage /> },
    { path: '/organization/departments', permission: 'organization.view_department', element: <DepartmentsPage /> },
    { path: '/inventory', permission: 'inventory.view_stockbalance', element: <InventoryPage /> },
    { path: '/inventory/locations', permission: 'inventory.view_stocklocation', element: <InventoryLocationsPage /> },
    { path: '/inventory/movements', permission: 'inventory.view_stockmovement', element: <InventoryMovementsPage /> },
    { path: '/inventory/transfer', permission: 'inventory.transfer_stock', element: <InventoryTransferPage /> },
    { path: '/payments', permission: 'payments.view_paymenttransaction', element: <PaymentsPage /> },
    { path: '/payments/:id', permission: 'payments.view_paymenttransaction', element: <PaymentDetailsPage /> },
    { path: '/payments/collect', permission: 'payments.process_collection', element: <CollectPaymentPage /> },
    { path: '/payments/supplier', permission: 'purchases.process_supplier_payment', element: <SupplierPaymentPage /> },
    { path: '/accounting', permission: 'accounting.view_financial_reports', element: <AccountingHomePage /> },
    { path: '/accounting/accounts', permission: 'accounting.view_account', element: <AccountsPage /> },
    { path: '/accounting/journals', permission: 'accounting.view_journalentry', element: <JournalsPage /> },
    { path: '/accounting/ledger', permission: 'accounting.view_financial_reports', element: <GeneralLedgerPage /> },
    { path: '/accounting/trial-balance', permission: 'accounting.view_financial_reports', element: <TrialBalancePage /> },
    { path: '/accounting/statements', permission: 'accounting.view_financial_reports', element: <StatementsPage /> },
    { path: '/accounting/balances', permission: 'accounting.view_financial_reports', element: <BalancesPage /> },
    { path: '/accounting/expenses', permission: 'accounting.view_expense', element: <ExpensesPage /> },
    { path: '/accounting/periods', permission: 'accounting.view_accountingperiod', element: <PeriodsPage /> },
    { path: '/accounting/opening-balance', permission: 'accounting.manage_chart_of_accounts', element: <OpeningBalancePage /> },
    { path: '/accounting/manual-journal', permission: 'accounting.add_journalentry', element: <ManualJournalPage /> },
  ];

  return <AppErrorBoundary><Authenticated user={user!}><Routes>{securedRoutes.map(({ path, permission, element }) => <Route key={path} path={path} element={<ProtectedPage user={user!} permission={permission}>{element}</ProtectedPage>} />)}<Route path="*" element={<NotFound />} /></Routes></Authenticated></AppErrorBoundary>;
}
