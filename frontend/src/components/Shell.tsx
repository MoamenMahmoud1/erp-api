import type { ReactNode } from 'react';
import { useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  ActionIcon,
  AppShell,
  Avatar,
  Burger,
  Divider,
  Group,
  Menu,
  NavLink,
  ScrollArea,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  Tooltip,
  useMantineColorScheme,
} from '@mantine/core';
import {
  IconBook,
  IconBox,
  IconBuilding,
  IconChartBar,
  IconChevronDown,
  IconDashboard,
  IconFileInvoice,
  IconMoon,
  IconPackage,
  IconPower,
  IconReceipt,
  IconSearch,
  IconShoppingCart,
  IconSun,
  IconTruck,
  IconUsers,
  IconWallet,
} from '@tabler/icons-react';

import { api, type UserProfile } from '../lib/api';

type NavItem = {
  label: string;
  to: string;
  icon: ReactNode;
};

type NavSection = {
  label: string;
  items: NavItem[];
};

const sections: NavSection[] = [
  {
    label: 'Workspace',
    items: [
      { label: 'Dashboard', to: '/', icon: <IconDashboard size={17} /> },
      { label: 'Sales', to: '/sales', icon: <IconReceipt size={17} /> },
      { label: 'Purchases', to: '/purchases', icon: <IconShoppingCart size={17} /> },
    ],
  },
  {
    label: 'Master data',
    items: [
      { label: 'Products', to: '/products', icon: <IconBox size={17} /> },
      { label: 'Customers', to: '/customers', icon: <IconUsers size={17} /> },
      { label: 'Suppliers', to: '/suppliers', icon: <IconTruck size={17} /> },
      { label: 'Employees', to: '/employees', icon: <IconUsers size={17} /> },
    ],
  },
  {
    label: 'Operations',
    items: [
      { label: 'Inventory', to: '/inventory', icon: <IconPackage size={17} /> },
      { label: 'Payments', to: '/payments', icon: <IconWallet size={17} /> },
      { label: 'Organization', to: '/organization/company', icon: <IconBuilding size={17} /> },
    ],
  },
  {
    label: 'Accounting',
    items: [
      { label: 'Overview', to: '/accounting', icon: <IconChartBar size={17} /> },
      { label: 'Accounts', to: '/accounting/accounts', icon: <IconBook size={17} /> },
      { label: 'Journals', to: '/accounting/journals', icon: <IconFileInvoice size={17} /> },
      { label: 'Statements', to: '/accounting/statements', icon: <IconChartBar size={17} /> },
      { label: 'AR / AP', to: '/accounting/balances', icon: <IconWallet size={17} /> },
    ],
  },
];

const allItems = sections.flatMap((section) => section.items);

export function Shell({ user, children }: { user: UserProfile; children: ReactNode }) {
  const [opened, setOpened] = useState(false);
  const [search, setSearch] = useState('');
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  const location = useLocation();
  const navigate = useNavigate();
  const dark = colorScheme === 'dark';

  const searchMatches = useMemo(() => {
    const value = search.trim().toLowerCase();
    if (!value) return [];
    return allItems.filter((item) => item.label.toLowerCase().includes(value)).slice(0, 5);
  }, [search]);

  async function logout() {
    try {
      await api.auth.logout();
    } finally {
      navigate('/login');
    }
  }

  function submitSearch() {
    if (!searchMatches.length) return;
    navigate(searchMatches[0].to);
    setSearch('');
  }

  return (
    <div className="app-bg">
      <div className="aurora-orb one" />
      <div className="aurora-orb two" />
      <div className="aurora-orb three" />

      <AppShell
        padding="lg"
        navbar={{ width: 238, breakpoint: 'md', collapsed: { mobile: !opened } }}
        header={{ height: 74 }}
        styles={{
          main: { background: 'transparent' },
          header: {
            background: dark ? 'rgba(8, 13, 25, 0.88)' : 'rgba(255, 255, 255, 0.92)',
            backdropFilter: 'blur(12px)',
            borderColor: dark ? 'rgba(148, 163, 184, 0.10)' : 'rgba(15, 23, 42, 0.07)',
          },
          navbar: {
            background: dark ? 'rgba(8, 13, 25, 0.94)' : 'rgba(255, 255, 255, 0.95)',
            borderColor: dark ? 'rgba(148, 163, 184, 0.10)' : 'rgba(15, 23, 42, 0.07)',
          },
        }}
      >
        <AppShell.Header>
          <Group h="100%" px="lg" justify="space-between" gap="lg">
            <Group gap="sm" miw={230}>
              <Burger opened={opened} onClick={() => setOpened((value) => !value)} hiddenFrom="md" size="sm" />
              <Group gap="sm">
                <ThemeIcon variant="gradient" gradient={{ from: 'indigo', to: 'cyan', deg: 120 }} size={36} radius="xl">
                  E
                </ThemeIcon>
                <div>
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
              onKeyDown={(event) => {
                if (event.key === 'Enter') submitSearch();
                if (event.key === 'Escape') setSearch('');
              }}
              visibleFrom="sm"
              styles={{ input: { borderRadius: 999 } }}
            />

            <Group gap="xs">
              <Tooltip label={dark ? 'Use light theme' : 'Use dark theme'}>
                <ActionIcon variant="subtle" radius="xl" size="lg" onClick={() => toggleColorScheme()} aria-label="Toggle color scheme">
                  {dark ? <IconSun size={18} /> : <IconMoon size={18} />}
                </ActionIcon>
              </Tooltip>

              <Menu shadow="md" width={210} position="bottom-end">
                <Menu.Target>
                  <button className="user-chip" type="button">
                    <Avatar radius="xl" size="sm" color="indigo">
                      {(user.first_name || user.username).slice(0, 1).toUpperCase()}
                    </Avatar>
                    <span className="user-chip-copy">
                      <Text size="sm" fw={750}>{user.first_name || user.username}</Text>
                      <Text size="xs" c="dimmed">{user.email}</Text>
                    </span>
                    <IconChevronDown size={15} />
                  </button>
                </Menu.Target>
                <Menu.Dropdown>
                  <Menu.Label>Account</Menu.Label>
                  <Menu.Item leftSection={<IconPower size={16} />} color="red" onClick={logout}>Sign out</Menu.Item>
                </Menu.Dropdown>
              </Menu>
            </Group>
          </Group>
        </AppShell.Header>

        <AppShell.Navbar p="sm">
          <AppShell.Section grow component={ScrollArea} scrollbarSize={4}>
            <Stack gap="md">
              {sections.map((section) => (
                <div key={section.label}>
                  <Text px="sm" mb={6} size="xs" fw={800} tt="uppercase" c="dimmed" lts="0.08em">
                    {section.label}
                  </Text>
                  <Stack gap={2}>
                    {section.items.map((item) => {
                      const active = location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to));
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
                          radius="md"
                          styles={{
                            root: { minHeight: 40 },
                            label: { fontWeight: active ? 750 : 600 },
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
            <Text size="xs" c="dimmed" px="sm">ERP workspace</Text>
          </AppShell.Section>
        </AppShell.Navbar>

        {searchMatches.length > 0 && (
          <div className="search-results">
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
