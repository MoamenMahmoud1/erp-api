import type { ReactNode } from 'react';
import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  ActionIcon,
  AppShell,
  Avatar,
  Burger,
  Button,
  Divider,
  Group,
  NavLink,
  ScrollArea,
  Stack,
  Text,
  ThemeIcon,
  Tooltip,
  useMantineColorScheme,
} from '@mantine/core';
import { IconChevronRight, IconMoon, IconPower, IconSun } from '@tabler/icons-react';

import { api, type UserProfile } from '../lib/api';

const sections = [
  {
    label: 'Command Center',
    items: [
      { label: 'Dashboard', to: '/', glyph: '⌂' },
      { label: 'Sales', to: '/sales', glyph: '↗' },
      { label: 'New invoice', to: '/sales/new', glyph: '+' },
      { label: 'Purchases', to: '/purchases', glyph: '↘' },
      { label: 'New purchase', to: '/purchases/new', glyph: '+' },
    ],
  },
  {
    label: 'Master Data',
    items: [
      { label: 'Products', to: '/products', glyph: '◈' },
      { label: 'Carton pricing', to: '/products/cartons', glyph: '▤' },
      { label: 'Customers', to: '/customers', glyph: '◉' },
      { label: 'Suppliers', to: '/suppliers', glyph: '◌' },
      { label: 'Coupons', to: '/coupons', glyph: '%' },
      { label: 'Employees', to: '/employees', glyph: '◇' },
    ],
  },
  {
    label: 'Organization',
    items: [
      { label: 'Company', to: '/organization/company', glyph: 'C' },
      { label: 'Sites', to: '/organization/sites', glyph: '⌂' },
      { label: 'Departments', to: '/organization/departments', glyph: 'D' },
    ],
  },
  {
    label: 'Operations',
    items: [
      { label: 'Inventory', to: '/inventory', glyph: '▦' },
      { label: 'Locations', to: '/inventory/locations', glyph: 'L' },
      { label: 'Movements', to: '/inventory/movements', glyph: '↔' },
      { label: 'Transfer stock', to: '/inventory/transfer', glyph: '→' },
      { label: 'Payments', to: '/payments', glyph: '$' },
      { label: 'Collect payment', to: '/payments/collect', glyph: '+' },
      { label: 'Pay supplier', to: '/payments/supplier', glyph: '−' },
    ],
  },
  {
    label: 'Accounting',
    items: [
      { label: 'Overview', to: '/accounting', glyph: 'Σ' },
      { label: 'Accounts', to: '/accounting/accounts', glyph: 'A' },
      { label: 'Journals', to: '/accounting/journals', glyph: 'J' },
      { label: 'General ledger', to: '/accounting/ledger', glyph: 'G' },
      { label: 'Trial balance', to: '/accounting/trial-balance', glyph: 'T' },
      { label: 'Statements', to: '/accounting/statements', glyph: 'R' },
      { label: 'AR / AP', to: '/accounting/balances', glyph: '≋' },
      { label: 'Expenses', to: '/accounting/expenses', glyph: 'E' },
      { label: 'Periods', to: '/accounting/periods', glyph: 'P' },
    ],
  },
];

export function Shell({ user, children }: { user: UserProfile; children: ReactNode }) {
  const [opened, setOpened] = useState(false);
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  const location = useLocation();
  const navigate = useNavigate();
  const dark = colorScheme === 'dark';

  async function logout() {
    try { await api.auth.logout(); } finally { navigate('/login'); }
  }

  return (
    <div className="app-bg">
      <div className="aurora-orb one" />
      <div className="aurora-orb two" />
      <div className="aurora-orb three" />

      <AppShell
        padding="lg"
        navbar={{ width: 260, breakpoint: 'md', collapsed: { mobile: !opened } }}
        header={{ height: 72 }}
        styles={{
          main: { background: 'transparent' },
          header: { background: dark ? 'rgba(7, 11, 23, 0.72)' : 'rgba(255, 255, 255, 0.82)', backdropFilter: 'blur(20px)', borderColor: 'rgba(148,163,184,0.10)' },
          navbar: { background: dark ? 'rgba(7, 11, 23, 0.72)' : 'rgba(255, 255, 255, 0.82)', backdropFilter: 'blur(20px)', borderColor: 'rgba(148,163,184,0.10)' },
        }}
      >
        <AppShell.Header>
          <Group h="100%" px="lg" justify="space-between">
            <Group gap="sm">
              <Burger opened={opened} onClick={() => setOpened((value) => !value)} hiddenFrom="md" size="sm" />
              <Group gap="xs">
                <ThemeIcon variant="gradient" gradient={{ from: 'indigo', to: 'cyan', deg: 120 }} size="md" radius="md">E</ThemeIcon>
                <div>
                  <Text fw={800} size="sm" lh={1}>ERP Command Center</Text>
                  <Text size="xs" c="dimmed">Sales & operations</Text>
                </div>
              </Group>
            </Group>
            <Group gap="sm">
              <Tooltip label={dark ? 'Use light theme' : 'Use dark theme'}>
                <ActionIcon variant="subtle" onClick={() => toggleColorScheme()}>{dark ? <IconSun size={18} /> : <IconMoon size={18} />}</ActionIcon>
              </Tooltip>
              <Group gap="xs" visibleFrom="sm"><Avatar radius="xl" color="indigo">{(user.first_name || user.username).slice(0, 1).toUpperCase()}</Avatar><div><Text size="sm" fw={700}>{user.first_name || user.username}</Text><Text size="xs" c="dimmed">{user.email}</Text></div></Group>
              <Tooltip label="Sign out"><ActionIcon variant="subtle" color="red" onClick={logout}><IconPower size={18} /></ActionIcon></Tooltip>
            </Group>
          </Group>
        </AppShell.Header>

        <AppShell.Navbar p="md">
          <AppShell.Section grow component={ScrollArea} scrollbarSize={4}>
            <Stack gap="lg">
              {sections.map((section) => (
                <div key={section.label}>
                  <Text px="sm" mb={6} size="xs" fw={800} tt="uppercase" c="dimmed" lts="0.08em">{section.label}</Text>
                  <Stack gap={3}>
                    {section.items.map((item) => {
                      const active = location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to));
                      return <NavLink key={item.to} component={Link} to={item.to} active={active} label={item.label} leftSection={<Text size="sm" fw={800} w={22} ta="center">{item.glyph}</Text>} rightSection={active ? <IconChevronRight size={14} /> : null} onClick={() => setOpened(false)} variant="light" />;
                    })}
                  </Stack>
                </div>
              ))}
            </Stack>
          </AppShell.Section>
          <AppShell.Section><Divider my="md" /><Button fullWidth variant="subtle" leftSection={<IconPower size={16} />} onClick={logout} color="gray">Sign out</Button></AppShell.Section>
        </AppShell.Navbar>

        <AppShell.Main className="page-enter">{children}</AppShell.Main>
      </AppShell>
    </div>
  );
}
