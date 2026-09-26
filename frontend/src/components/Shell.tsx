import type { ReactNode } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ActionIcon, AppShell, Avatar, Badge, Burger, Divider, Group, Menu, NavLink, ScrollArea, Stack, Text, TextInput, ThemeIcon, Tooltip, useMantineColorScheme } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconBell, IconBook, IconBox, IconBuilding, IconCalendarDue, IconChartBar, IconChevronDown, IconClock, IconDashboard, IconFileInvoice, IconMoon, IconPackage, IconPower, IconReceipt, IconSearch, IconSettings, IconShoppingCart, IconSun, IconTruck, IconUsers, IconWallet } from '@tabler/icons-react';

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
      { label: 'Purchases', to: '/purchases', icon: <IconShoppingCart size={17} />, permission: 'purchases.view_purchase' },
      { label: 'Payments', to: '/payments', icon: <IconWallet size={17} />, permission: 'payments.view_paymenttransaction' },
      { label: 'My shift', to: '/shift', icon: <IconClock size={17} />, permission: 'accounts.start_employee_shift', hideWithoutShift: true },
    ],
  },
  {
    label: 'Catalog',
    items: [
      { label: 'Products', to: '/products', icon: <IconBox size={17} />, permission: 'products.view_product' },
      { label: 'Carton pricing', to: '/products/cartons', icon: <IconPackage size={17} />, permission: 'products.view_cartonpricing' },
      { label: 'Customers', to: '/customers', icon: <IconUsers size={17} />, permission: 'customers.view_customer' },
      { label: 'Suppliers', to: '/suppliers', icon: <IconTruck size={17} />, permission: 'suppliers.view_supplier' },
      { label: 'Coupons', to: '/coupons', icon: <IconReceipt size={17} />, permission: 'coupons.view_coupon' },
    ],
  },
  {
    label: 'Inventory',
    items: [
      { label: 'Stock', to: '/inventory', icon: <IconPackage size={17} />, permission: 'inventory.view_stockbalance' },
      { label: 'Batches & expiry', to: '/inventory/batches', icon: <IconCalendarDue size={17} />, permission: 'inventory.view_stockbalance' },
      { label: 'Locations', to: '/inventory/locations', icon: <IconBuilding size={17} />, permission: 'inventory.view_stocklocation' },
      { label: 'Movements', to: '/inventory/movements', icon: <IconChartBar size={17} />, permission: 'inventory.view_stockmovement' },
    ],
  },
  {
    label: 'Organization',
    items: [
      { label: 'Company', to: '/organization/company', icon: <IconBuilding size={17} />, permission: 'organization.view_company' },
      { label: 'Sites', to: '/organization/sites', icon: <IconBuilding size={17} />, permission: 'organization.view_site' },
      { label: 'Departments', to: '/organization/departments', icon: <IconUsers size={17} />, permission: 'organization.view_department' },
      { label: 'Employees', to: '/employees', icon: <IconUsers size={17} />, permission: 'accounts.view_employee' },
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
    ],
  },
  {
    label: 'Accounting setup',
    items: [
      { label: 'Periods', to: '/accounting/periods', icon: <IconCalendarDue size={17} />, permission: 'accounting.view_accountingperiod' },
      { label: 'Opening balance', to: '/accounting/opening-balance', icon: <IconBook size={17} />, permission: 'accounting.manage_chart_of_accounts' },
      { label: 'Manual journal', to: '/accounting/manual-journal', icon: <IconFileInvoice size={17} />, permission: 'accounting.add_journalentry' },
    ],
  },
];

export function Shell({ user, children }: { user: UserProfile; children: ReactNode }) {
  const [opened, setOpened] = useState(false);
  const [search, setSearch] = useState('');
  const [adminLoading, setAdminLoading] = useState(false);
  const [webPushStatus, setWebPushStatus] = useState<'checking' | 'enabled' | 'available' | 'denied' | 'unsupported'>('checking');
  const [webPushLoading, setWebPushLoading] = useState(false);
  const [showWelcome, setShowWelcome] = useState(() => (
    typeof window !== 'undefined' && window.sessionStorage.getItem('erp-show-welcome') === '1'
  ));
  const [closingWelcome, setClosingWelcome] = useState(false);
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

  useEffect(() => {
    const webPush = window.erpWebPush;
    if (!webPush) {
      setWebPushStatus('unsupported');
      return;
    }

    const handleRegistered = async (event: Event) => {
      const detail = (event as CustomEvent<{ installationId?: string; firebaseAppId?: string }>).detail;
      if (!detail?.installationId) return;
      try {
        await api.notifications.registerDevice({
          installation_id: detail.installationId,
          platform: 'web',
          firebase_app_id: detail.firebaseAppId || '',
        });
        setWebPushStatus('enabled');
      } catch {
        // Push registration is best-effort; the core workspace remains usable.
      }
    };

    const handleUnregistered = async (event: Event) => {
      const detail = (event as CustomEvent<{ installationId?: string }>).detail;
      if (!detail?.installationId) return;
      try {
        await api.notifications.unregisterDevice(detail.installationId);
      } finally {
        setWebPushStatus('available');
      }
    };

    window.addEventListener('erp-webpush-registered', handleRegistered);
    window.addEventListener('erp-webpush-unregistered', handleUnregistered);
    window.addEventListener('erp-webpush-message', () => {
      window.dispatchEvent(new Event('erp-notifications-refresh'));
    });

    webPush.ready.then(async (state) => {
      if (state.permission === 'granted') {
        setWebPushStatus('enabled');
        try {
          await webPush.sync();
        } catch {
          setWebPushStatus('available');
        }
        return;
      }
      setWebPushStatus(
        state.permission === 'denied'
          ? 'denied'
          : state.permission === 'default'
            ? 'available'
            : 'unsupported',
      );
    });

    return () => {
      window.removeEventListener('erp-webpush-registered', handleRegistered);
      window.removeEventListener('erp-webpush-unregistered', handleUnregistered);
      // NotificationCenter owns the push-message listener; this effect only bridges push delivery to refresh state.
    };
  }, [user.id]);

  async function enableDesktopNotifications() {
    setWebPushLoading(true);
    try {
      const result = await window.erpWebPush?.enable({ requestPermission: true });
      if (result?.status === 'enabled') {
        setWebPushStatus('enabled');
        notifications.show({
          title: 'Desktop notifications enabled',
          message: 'This browser can now receive ERP push notifications.',
        });
      } else if (result?.status === 'denied') {
        setWebPushStatus('denied');
      } else {
        setWebPushStatus('unsupported');
      }
    } catch {
      notifications.show({
        title: 'Notifications unavailable',
        message: 'The browser could not enable ERP push notifications.',
      });
    } finally {
      setWebPushLoading(false);
    }
  }

  async function logout() {
    try {
      const installationId = await window.erpWebPush?.disable();
      if (installationId) {
        await api.notifications.unregisterDevice(installationId);
      }
    } catch {
      // Continue logout even if push cleanup fails.
    }
    try { await api.auth.logout(); } finally { navigate('/login'); }
  }

  function submitSearch() {
    if (!searchMatches.length) return;
    navigate(searchMatches[0].to);
    setSearch('');
  }

  async function openAdmin() {
    setAdminLoading(true);
    try {
      const result = await api.auth.openAdmin();
      window.location.assign(result.url);
    } finally {
      setAdminLoading(false);
    }
  }

  const roleLabel = user.role?.name || (user.is_superuser ? 'Administrator' : 'User');
  const siteLabel = user.employee?.site?.name || 'Company-wide';
  const firstName = user.first_name || user.username;
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  const dateLabel = new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  }).format(new Date());

  function dismissWelcome() {
    if (closingWelcome) return;
    if (typeof window !== 'undefined') window.sessionStorage.removeItem('erp-show-welcome');
    setClosingWelcome(true);
    window.setTimeout(() => {
      setShowWelcome(false);
      setClosingWelcome(false);
    }, 320);
  }

  return (
    <div className="app-bg">
      <AppShell
        padding={{ base: 'sm', md: 'lg' }}
        navbar={{ width: 244, breakpoint: 'md', collapsed: { mobile: !opened } }}
        header={{ height: 68 }}
        styles={{
          main: { background: 'transparent' },
          header: { background: 'var(--erp-surface)', borderColor: 'var(--erp-border)' },
          navbar: { background: 'var(--erp-surface)', borderColor: 'var(--erp-border)' },
        }}
      >
        <AppShell.Header>
          <Group h="100%" px={{ base: 'sm', md: 'lg' }} justify="space-between" gap="sm">
            <Group gap="sm" miw={{ base: 'auto', sm: 220 }}>
              <Burger opened={opened} onClick={() => setOpened((value) => !value)} hiddenFrom="md" size="sm" aria-label="Open navigation" />
              <Group gap="sm">
                <ThemeIcon color="erp" variant="light" size={34} radius="sm">E</ThemeIcon>
                <div className="brand-copy">
                  <Text fw={750} size="sm" lh={1.1}>ERP Workspace</Text>
                  <Text size="xs" c="dimmed" mt={2}>Sales & operations</Text>
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
              styles={{ input: { borderRadius: 'var(--erp-radius-sm)' } }}
            />
            <Group gap="xs">
              <NotificationCenter
                webPushStatus={webPushStatus}
                webPushLoading={webPushLoading}
                onEnableDesktopNotifications={enableDesktopNotifications}
              />
              <Tooltip label={dark ? 'Use light theme' : 'Use dark theme'}>
                <ActionIcon variant="subtle" radius="sm" size="lg" onClick={() => toggleColorScheme()} aria-label="Toggle color scheme">
                  {dark ? <IconSun size={18} /> : <IconMoon size={18} />}
                </ActionIcon>
              </Tooltip>
              <Menu shadow="md" width={280} position="bottom-end">
                <Menu.Target>
                  <button className="user-chip" type="button" aria-label="Open account menu">
                    <Avatar radius="sm" size="sm" color="erp">{(user.first_name || user.username).slice(0, 1).toUpperCase()}</Avatar>
                    <span className="user-chip-copy">
                      <Text size="sm" fw={700}>{user.first_name || user.username}</Text>
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
                  {user.is_superuser && (
                    <>
                      <Menu.Divider />
                      <Menu.Label>Administration</Menu.Label>
                      <Menu.Item
                        leftSection={<IconSettings size={16} />}
                        disabled={adminLoading}
                        onClick={openAdmin}
                      >
                        {adminLoading ? 'Opening admin…' : 'Admin'}
                      </Menu.Item>
                    </>
                  )}
                  <Menu.Divider />
                  <Menu.Label>Account</Menu.Label>
                  <Menu.Item
                    leftSection={<IconBell size={16} />}
                    disabled={webPushStatus === 'denied' || webPushStatus === 'unsupported' || webPushLoading}
                    onClick={enableDesktopNotifications}
                  >
                    {webPushStatus === 'enabled'
                      ? 'Desktop notifications enabled'
                      : webPushStatus === 'denied'
                        ? 'Notifications blocked'
                        : webPushLoading
                          ? 'Enabling notifications…'
                          : 'Enable desktop notifications'}
                  </Menu.Item>
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
                  <Text px="sm" mb={6} size="xs" fw={750} tt="uppercase" c="dimmed" lts="0.07em">{section.label}</Text>
                  <Stack gap={1}>
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
                          variant="subtle"
                          styles={{
                            root: { minHeight: 36, borderRadius: 'var(--erp-radius-sm)' },
                            label: { fontWeight: active ? 700 : 550 },
                          }}
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

        <AppShell.Main className="page-enter">
          {showWelcome && (
            <section className={`welcome-panel${closingWelcome ? ' is-closing' : ''}`} aria-label="Welcome to ERP Workspace">
              <div className="welcome-copy">
                <div className="welcome-kicker">
                  <span className="welcome-status-dot" aria-hidden="true" />
                  <Text size="xs" fw={800} tt="uppercase" lts=".11em">Workspace ready</Text>
                </div>
                <Text className="welcome-title" fw={850}>{greeting}, {firstName}.</Text>
                <Text className="welcome-subtitle">
                  Your workspace is ready. Review the numbers, control stock, and keep every transaction traceable.
                </Text>
                <Group className="welcome-meta" gap="xs" wrap="wrap">
                  <span>{roleLabel}</span>
                  <span>{siteLabel}</span>
                  <span>{user.current_shift ? 'Shift open' : 'No active shift'}</span>
                  <span>{dateLabel}</span>
                </Group>
              </div>

              <div className="welcome-visual" aria-hidden="true">
                <div className="welcome-visual-label">
                  <span>CONTROL VIEW</span>
                  <strong>Operational pulse</strong>
                </div>
                <svg className="welcome-ledger-chart" viewBox="0 0 440 180" role="presentation">
                  <g className="welcome-grid">
                    <path d="M12 28H428M12 76H428M12 124H428" />
                    <path d="M84 12V156M188 12V156M292 12V156M396 12V156" />
                  </g>
                  <path className="welcome-chart-line" d="M14 132 C48 126, 56 102, 88 108 S128 122, 154 92 S194 62, 222 78 S256 112, 286 72 S330 34, 360 56 S394 64, 426 28" />
                  <path className="welcome-chart-base" d="M14 148H426" />
                  <circle className="welcome-chart-point" cx="426" cy="28" r="5" />
                </svg>
                <div className="welcome-visual-footer">
                  <span>Sales</span>
                  <span>Inventory</span>
                  <span>Accounting</span>
                </div>
              </div>

              <button className="welcome-dismiss" type="button" onClick={dismissWelcome} aria-label="Dismiss welcome panel">×</button>
            </section>
          )}
          {children}
        </AppShell.Main>
      </AppShell>
    </div>
  );
}
