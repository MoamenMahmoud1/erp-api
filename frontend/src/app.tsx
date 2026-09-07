import type { ErrorInfo, ReactNode } from 'react';
import { Component, useEffect, useRef, useState } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { Button, Card, Center, Stack, Text, Loader } from '@mantine/core';

import { Shell } from './components/Shell';
import { RecordsPage } from './components/RecordsPage';
import { api, type UserProfile } from './lib/api';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from './pages/LoginPage';
import { ProductsPage, CustomersPage, SuppliersPage } from './pages/MasterDataPages';
import { CartonPricingPage, CouponsPage } from './pages/CommercialPages';
import { SalesPage, PurchasesPage, PaymentsPage, InventoryPage } from './pages/OperationsPages';
import { InventoryLocationsPage, InventoryMovementsPage, InventoryTransferPage } from './pages/InventoryPages';
import { CreateInvoicePage, CreatePurchasePage, CollectPaymentPage, SupplierPaymentPage } from './pages/TransactionPages';
import { AccountingHomePage, AccountsPage, JournalsPage, StatementsPage } from './pages/AccountingPages';
import { BalancesPage, OpeningBalancePage, ManualJournalPage } from './pages/AccountingReportsPages';
import { ExpensesPage, PeriodsPage, GeneralLedgerPage, TrialBalancePage } from './pages/AccountingOperationsPages';
import { CompanyPage, SitesPage, DepartmentsPage } from './pages/OrganizationPages';

class AppErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ERP frontend error', error, info);
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <Center mih="100vh" p="xl">
        <Card className="glass" radius="xl" withBorder p="xl" maw={620}>
          <Stack gap="sm">
            <Text size="sm" fw={800} c="red.5" tt="uppercase" lts=".08em">Application error</Text>
            <Text size="xl" fw={800}>Something went wrong in this screen.</Text>
            <Text c="dimmed">The page crashed instead of leaving a blank screen. Reload it and, if it repeats, the message below identifies the runtime error.</Text>
            {import.meta.env.DEV && <Text size="sm" ff="monospace" c="dimmed">{this.state.error.message}</Text>}
            <Button onClick={() => window.location.reload()}>Reload workspace</Button>
          </Stack>
        </Card>
      </Center>
    );
  }
}

function Authenticated({ user, children }: { user: UserProfile; children: ReactNode }) {
  return <Shell user={user}>{children}</Shell>;
}

function EmployeesPage() {
  return <RecordsPage eyebrow="MASTER DATA" title="Employees" subtitle="Staff directory and account access visibility." list={api.employees.list} columns={[{ key: 'id', label: '#' }, { key: 'username', label: 'Username' }, { key: 'email', label: 'Email' }, { key: 'first_name', label: 'First name' }, { key: 'last_name', label: 'Last name' }, { key: 'is_staff', label: 'Staff' }]} />;
}

function NotFound() {
  return <Center h="60vh"><div><h2>Page not found</h2><p>This route is not part of the current ERP workspace.</p></div></Center>;
}

export function App() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();
  const authCheckStarted = useRef(false);

  useEffect(() => {
    if (location.pathname === '/login') {
      setLoading(false);
      return;
    }
    if (user || authCheckStarted.current) return;

    authCheckStarted.current = true;
    api.auth.me()
      .then(setUser)
      .catch(() => {
        setUser(null);
        navigate('/login', { replace: true });
      })
      .finally(() => setLoading(false));
  }, [location.pathname, navigate, user]);

  if (loading) return <Center h="100vh"><Loader size="lg" /></Center>;
  if (!user && location.pathname !== '/login') return null;
  if (location.pathname === '/login') return user ? <Navigate to="/" replace /> : <LoginPage />;

  return (
    <AppErrorBoundary>
      <Authenticated user={user!}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />

          <Route path="/sales" element={<SalesPage />} />
          <Route path="/sales/new" element={<CreateInvoicePage />} />
          <Route path="/purchases" element={<PurchasesPage />} />
          <Route path="/purchases/new" element={<CreatePurchasePage />} />

          <Route path="/products" element={<ProductsPage />} />
          <Route path="/products/cartons" element={<CartonPricingPage />} />
          <Route path="/customers" element={<CustomersPage />} />
          <Route path="/suppliers" element={<SuppliersPage />} />
          <Route path="/coupons" element={<CouponsPage />} />
          <Route path="/employees" element={<EmployeesPage />} />

          <Route path="/organization/company" element={<CompanyPage />} />
          <Route path="/organization/sites" element={<SitesPage />} />
          <Route path="/organization/departments" element={<DepartmentsPage />} />

          <Route path="/inventory" element={<InventoryPage />} />
          <Route path="/inventory/locations" element={<InventoryLocationsPage />} />
          <Route path="/inventory/movements" element={<InventoryMovementsPage />} />
          <Route path="/inventory/transfer" element={<InventoryTransferPage />} />

          <Route path="/payments" element={<PaymentsPage />} />
          <Route path="/payments/collect" element={<CollectPaymentPage />} />
          <Route path="/payments/supplier" element={<SupplierPaymentPage />} />

          <Route path="/accounting" element={<AccountingHomePage />} />
          <Route path="/accounting/accounts" element={<AccountsPage />} />
          <Route path="/accounting/journals" element={<JournalsPage />} />
          <Route path="/accounting/ledger" element={<GeneralLedgerPage />} />
          <Route path="/accounting/trial-balance" element={<TrialBalancePage />} />
          <Route path="/accounting/statements" element={<StatementsPage />} />
          <Route path="/accounting/balances" element={<BalancesPage />} />
          <Route path="/accounting/expenses" element={<ExpensesPage />} />
          <Route path="/accounting/periods" element={<PeriodsPage />} />
          <Route path="/accounting/opening-balance" element={<OpeningBalancePage />} />
          <Route path="/accounting/manual-journal" element={<ManualJournalPage />} />

          <Route path="*" element={<NotFound />} />
        </Routes>
      </Authenticated>
    </AppErrorBoundary>
  );
}
