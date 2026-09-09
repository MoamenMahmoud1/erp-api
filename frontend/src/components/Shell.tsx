import type { ReactNode } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ActionIcon, AppShell, Avatar, Badge, Burger, Divider, Group, Menu, NavLink, ScrollArea, Stack, Text, TextInput, ThemeIcon, Tooltip, useMantineColorScheme } from '@mantine/core';
import { IconBook, IconBox, IconBuilding, IconCalendarDue, IconChartBar, IconChevronDown, IconClock, IconDashboard, IconFileInvoice, IconMoon, IconPackage, IconPower, IconReceipt, IconSearch, IconShoppingCart, IconSun, IconTruck, IconUsers, IconWallet } from '@tabler/icons-react';

import { can } from './PermissionGuard';
import { api, type UserProfile } from '../lib/api';

type NavItem = { label: string; to: string; icon: ReactNode; permission: string; hideWithoutShift?: boolean };
type NavSection = { label: string; items: NavItem[] };

const sections: NavSection[] = [
  {
    label: 'Workspace',
    items: [
      { label: 'Dashboard', to: '/', icon: <IconDashboard size={17} />, permission: 'accounting.view_financial_reports' },
      { label: 'Insights', to: '/insights', icon: <IconChartBar size={17} />, permission: 'accounting.view_financial_reports' },
      { label: 'Sales', to: '/sales', icon: <IconReceipt size={17} />, permission: 'invoices.view_invoice' },
      { label: 'New sale', to: '/sales/new', icon: <IconReceipt size={17} />, permission: 'invoices.add_invoice' },
      { label: 'Purchases', to: '/purchases', icon: <IconShoppingCart size={17} />, permission: 'purchases.view_purchase' },
      { label: 'New purchase', to: '/purchases/new', icon: <IconShoppingCart size={17} />, permission: 'purchases.add_purchase' },
      { label: 'Collect payment', to: '/payments/collect', icon: <IconWallet size={17} />, permission: 'payments.process_collection' },
      { label: 'Pay supplier', to: '/payments/supplier', icon: <IconTruck size={17} />, permission: 'purchases.process_supplier_payment' },
      { label: 'My Shift', to: '/shift', icon: <IconClock size={17} />, permission: 'accounts.start_employee_shift', hideWithoutShift: false },
    ],
  },
  {
    label: 'Master data',
    items: [
      { label: 'Products', to: '/products', icon: <IconBox size={17} />, permission: 'products.view_product' },
      { label: 'Carton pricing', to: '/products/cartons', icon: <IconPackage size={17} />, permission: 'products.view_cartonpricing' },
      { label: 'Customers', to: '/customers', icon: <IconUsers size={17} />, permission: 'customers.view_customer' },
      { label: 'Suppliers', to: '/suppliers', icon: <IconTruck size={17} />, permission: 'suppliers.view_supplier' },
      { label: 'Employees', to: '/employees', icon: <IconUsers size={17} />, permission: 'accounts.view_employee' },
      { label: 'Coupons', to: '/coupons', icon: <IconReceipt size={17} />, permission: 'coupons.view_coupon' },
    ],
  },
  {
    label: 'Operations',
    items: [
      { label: 'Inventory', to: '/inventory', icon: <IconPackage size={17} />, permission: 'inventory.view_stockbalance' },
      { label: 'Batches & expiry', to: '/inventory/batches', icon: <IconCalendarDue size={17} />, permission: 'inventory.view_stockbalance' },
      { label: 'Locations', to: '/inventory/locations', icon: <IconBuilding size={17} />, permission: 'inventory.view_stocklocation' },
      { label: 'Movements', to: '/inventory/movements', icon: <IconChartBar size={17} />, permission: 'inventory.view_stockmovement' },
      { label: 'Transfer stock', to: '/inventory/transfer', icon: <IconTruck size={17} />, permission: 'inventory.transfer_stock' },
      { label: 'Payments', to: '/payments', icon: <IconWallet size={17} />, permission: 'payments.view_paymenttransaction' },
      { label: 'Company', to: '/organization/company', icon: <IconBuilding size={17} />, permission: 'organization.view_company' },
      { label: 'Sites', to: '/organization/sites', icon: <IconBuilding size={17} />, permission: 'organization.view_site' },
      { label: 'Departments', to: '/organization/departments', icon: <IconUsers size={17} />, permission: 'organization.view_department' },
    ],
  },
  {
    label: 'Accounting',
    items: [
      { label: 'Overview', to: '/accounting', icon: <IconChartBar size={17} />, permission: 'accounting.view_financial_reports' },
      { label: 'Accounts', to: '/accounting/accounts', icon: <IconBook size={17} />, permission: 'accounting.view_account' },
      { label: 'Journals', to: '/accounting/journals', icon: <IconFileInvoice size={17} />, permission: 'accounting.view_journalentry' },
      { label: 'General ledger', to: '/accounting/ledger', icon: <IconBook size={17} />, permission: 'accounting.view_financial_reports' },
      { label: 'Trial balance', to: '/accounting/trial-balance', icon: <IconChartBar size={17} />, permission: 'accounting.view_financial_reports' },
      { label: 'Statements', to: '/accounting/statements', icon: <IconChartBar size={17} />, permission: 'accounting.view_financial_reports' },
      { label: 'AR / AP', to: '/accounting/balances', icon: <IconWallet size={17} />, permission: 'accounting.view_financial_reports' },
      { label: 'Expenses', to: '/accounting/expenses', icon: <IconWallet size={17} />, permission: 'accounting.view_expense' },
      { label: 'Periods', to: '/accounting/periods', icon: <IconCalendarDue size={17} />, permission: 'accounting.view_accountingperiod' },
      { label: 'Opening balance', to: '/accounting/opening-balance', icon: <IconBook size={17} />, permission: 'accounting.manage_chart_of_accounts' },
      { label: 'Manual journal', to: '/accounting/manual-journal', icon: <IconFileInvoice size={17} />, permission: 'accounting.add_journalentry' },
    ],
  },
];

export function Shell({ user, children }: { user: UserProfile; children: ReactNode }) {
  const [opened, setOpened] = useState(false);
  const [search, setSearch] = useState('');
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  const location = useLocation();
  const navigate = useNavigate();
  const dark = colorScheme === 'dark';

  const visibleSections = useMemo(
    () => sections
      .map((section) => ({
        ...section,
        items: section.items.filter((item) => can(user, item.permission) && (!item.hideWithoutShift || user.role?.requires_shift)),
      }))
      .filter((section) => section.items.length > 0),
    [user],
  );
  const allItems = useMemo(() => visibleSections.flatMap((section) => section.items), [visibleSections]);
  const searchMatches = useMemo(() => {
    const value = search.trim().toLowerCase();
    if (!value) return [];
    return allItems.filter((item) => item.label.toLowerCase().includes(value)).slice(0, 6);
  }, [allItems, search]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        document.querySelector<HTMLInputElement>('.topbar-search input')?.focus();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => {
    setSearch('');
    setOpened(false);
  }, [location.pathname]);

  async function logout() {
    try { await api.auth.logout(); } finally { navigate('/login'); }
  }

  function submitSearch() {
    if (!searchMatches.length) return;
    navigate(searchMatches[0].to);
    setSearch('');
  }

  const roleLabel = user.role?.name || (user.is_superuser ? 'Administrator' : 'User');
  const siteLabel = user.employee?.site?.name || 'Company-wide';

  return (
    <div className="app-bg">
      <div className="aurora-orb one" />
      <div className="aurora-orb two" />
      <div className="aurora-orb three" />
      <AppShell
        padding={{ base: 'sm', md: 'lg' }}
        navbar={{ width: 258, breakpoint: 'md', collapsed: { mobile: !opened } }}
        header={{ height: 74 }}
        styles={{
          main: { background: 'transparent' },
          header: {
            background: dark ? 'rgba(8, 13, 25, 0.90)' : 'rgba(255, 255, 255, 0.94)',
            backdropFilter: 'blur(12px)',
            borderColor: dark ? 'rgba(148, 163, 184, 0.10)' : 'rgba(15, 23, 42, 0.07)',
          },
          navbar: {
            background: dark ? 'rgba(8, 13, 25, 0.96)' : 'rgba(255, 255, 255, 0.97)',
            borderColor: dark ? 'rgba(148, 163, 184, 0.10)' : 'rgba(15, 23, 42, 0.07)',
          },
        }}
      >
        <AppShell.Header>
          <Group h="100%" px={{ base: 'sm', md: 'lg' }} justify="space-between" gap="sm">
            <Group gap="sm" miw={{ base: 'auto', sm: 230 }}>
              <Burger opened={opened} onClick={() => setOpened((value) => !value)} hiddenFrom="md" size="sm" aria-label="Open navigation" />
              <Group gap="sm">
                <ThemeIcon variant="gradient" gradient={{ from: 'indigo', to: 'cyan', deg: 120 }} size={36} radius="xl">E</ThemeIcon>
                <div className="brand-copy">
                  <Text fw={850} size="sm" lh={1.1}>ERP Command Center</Text>
                  <Text size="xs" c="dimmed" mt={3}>Sales & operations</Text>
                </div>
              </Group>
            </Group>
            <TextInput
              className="topbar-search"
              leftSection={<IconSearch size={17} />}
              rightSection={<Text size="xs" c="dimmed" className="shortcut-hint">⌘ K</Text>}
              placeholder="Search modules…"
              value={search}
              onChange={(event) => setSearch(event.currentTarget.value)}
              onKeyDown={(event) => { if (event.key === 'Enter') submitSearch(); if (event.key === 'Escape') setSearch(''); }}
              visibleFrom="sm"
              aria-label="Search modules"
              styles={{ input: { borderRadius: 999 } }}
            />
            <Group gap="xs">
              <Tooltip label={dark ? 'Use light theme' : 'Use dark theme'}>
                <ActionIcon variant="subtle" radius="xl" size="lg" onClick={() => toggleColorScheme()} aria-label="Toggle color scheme">
                  {dark ? <IconSun size={18} /> : <IconMoon size={18} />}
                </ActionIcon>
              </Tooltip>
              <Menu shadow="md" width={280} position="bottom-end">
                <Menu.Target>
                  <button className="user-chip" type="button" aria-label="Open account menu">
                    <Avatar radius="xl" size="sm" color="indigo">{(user.first_name || user.username).slice(0, 1).toUpperCase()}</Avatar>
                    <span className="user-chip-copy">
                      <Text size="sm" fw={750}>{user.first_name || user.username}</Text>
                      <Text size="xs" c="dimmed">{roleLabel} · {siteLabel}</Text>
                    </span>
                    <IconChevronDown size={15} />
                  </button>
                </Menu.Target>
                <Menu.Dropdown>
                  <Menu.Label>Workspace</Menu.Label>
                  <Menu.Item closeMenuOnClick={false} disabled leftSection={<IconBuilding size={16} />} rightSection={user.current_shift ? <Badge color="teal" size="sm">Shift open</Badge> : undefined}>
                    {siteLabel}
                  </Menu.Item>
                  <Menu.Divider />
                  <Menu.Label>Account</Menu.Label>
                  <Menu.Item leftSection={<IconPower size={16} />} color="red" onClick={logout}>Sign out</Menu.Item>
                </Menu.Dropdown>
              </Menu>
            </Group>
          </Group>
        </AppShell.Header>

        <AppShell.Navbar p="sm">
          <AppShell.Section grow component={ScrollArea} scrollbarSize={4} offsetScrollbars>
            <Stack gap="lg">
              {visibleSections.map((section) => (
                <div key={section.label}>
                  <Text px="sm" mb={7} size="xs" fw={800} tt="uppercase" c="dimmed" lts="0.08em">{section.label}</Text>
                  <Stack gap={2}>
                    {section.items.map((item) => {
                      const active = item.to === '/' ? location.pathname === '/' : location.pathname === item.to || location.pathname.startsWith(`${item.to}/`);
                      return (
                        <NavLink
                          key={item.to}
                          component={Link}
                          to={item.to}
                          active={active}
                          label={item.label}
                          leftSection={<span className="nav-icon">{item.icon}</span>}
                          onClick={() => setOpened(false)}
                          variant="light"
                          styles={{ root: { minHeight: 40, borderRadius: 10 }, label: { fontWeight: active ? 750 : 600 } }}
                        />
                      );
                    })}
                  </Stack>
                </div>
              ))}
            </Stack>
          </AppShell.Section>
          <AppShell.Section>
            <Divider my="md" />
            <Group justify="space-between" px="sm">
              <Text size="xs" c="dimmed">ERP workspace</Text>
              {user.current_shift && <Badge size="xs" variant="light" color="teal">On shift</Badge>}
            </Group>
          </AppShell.Section>
        </AppShell.Navbar>

        {searchMatches.length > 0 && (
          <div className="search-results" role="listbox">
            {searchMatches.map((item) => (
              <button key={item.to} type="button" onClick={() => { navigate(item.to); setSearch(''); }}>
                <span className="nav-icon">{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        )}

        <AppShell.Main className="page-enter">{children}</AppShell.Main>
      </AppShell>
    </div>
  );
}
