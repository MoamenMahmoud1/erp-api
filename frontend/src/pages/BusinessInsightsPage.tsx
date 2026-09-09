import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { Badge, Card, Group, Loader, SimpleGrid, Stack, Text, ThemeIcon, Title } from '@mantine/core';
import { IconArrowDownRight, IconArrowUpRight, IconCalendarDue, IconUsers } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';

import { api, query, type DashboardOverview } from '../lib/api';

const money = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const number = new Intl.NumberFormat('en-US');
const asMoney = (value: unknown) => money.format(Number(value || 0));
const isoLocal = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;

function MetricCard({ title, value, subtitle, icon, color = 'indigo' }: { title: string; value: string; subtitle: string; icon: ReactNode; color?: string }) {
  return <Card className="surface-panel bento-card" radius="xl" p="lg" withBorder><Group justify="space-between" align="flex-start"><div><Text size="xs" fw={800} c="dimmed" tt="uppercase" lts=".08em">{title}</Text><Text fw={900} size="clamp(1.5rem, 3vw, 2.1rem)" mt={6}>{value}</Text><Text size="xs" c="dimmed" mt={4}>{subtitle}</Text></div><ThemeIcon size={42} radius="lg" color={color} variant="light">{icon}</ThemeIcon></Group></Card>;
}

function CustomerList({ title, subtitle, rows, empty, tone }: { title: string; subtitle: string; rows: DashboardOverview['top_customers']; empty: string; tone: 'positive' | 'negative' }) {
  return <Card className="surface-panel bento-card" radius="xl" p="lg" withBorder><Text fw={800}>{title}</Text><Text size="xs" c="dimmed" mt={2}>{subtitle}</Text><Stack gap="sm" mt="lg">{rows.map((row, index) => <Group key={row.customer_id} justify="space-between" wrap="nowrap"><Group gap="sm" wrap="nowrap" miw={0}><Badge variant="light" radius="xl">{index + 1}</Badge><div style={{ minWidth: 0 }}><Text size="sm" fw={700} truncate>{row.customer_name}</Text><Text size="xs" c="dimmed">{row.invoice_count} invoices · {number.format(row.units_sold)} units</Text></div></Group><div style={{ textAlign: 'right' }}><Text size="sm" fw={850}>{asMoney(row.revenue)}</Text><Text size="xs" c={tone === 'positive' ? 'teal' : 'orange'}>{row.returns ? `Returns ${asMoney(row.returns)}` : 'No returns'}</Text></div></Group>)}{!rows.length && <Text size="sm" c="dimmed">{empty}</Text>}</Stack></Card>;
}

export function BusinessInsightsPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const now = new Date();
    const today = isoLocal(now);
    const monthStart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
    api.accounting.dashboardOverview(query({ from: monthStart, to: today }))
      .then(setData)
      .catch((error) => notifications.show({ title: 'Insights unavailable', message: error instanceof Error ? error.message : 'Unable to load analytics.', color: 'red' }))
      .finally(() => setLoading(false));
  }, []);

  if (loading && !data) return <Group justify="center" mih="50vh"><Loader /></Group>;
  if (!data) return null;

  const expiry = data.inventory.expiry_alerts.slice(0, 8);
  const expired = data.inventory.expired_alerts.slice(0, 6);

  return <Stack gap="xl">
    <div><Text size="sm" c="indigo.3" fw={800} tt="uppercase" lts=".08em">Intelligence</Text><Title order={1} mt={4}>Business insights</Title><Text c="dimmed" mt={4}>Know who drives revenue, who needs attention, and what stock needs action.</Text></div>
    <SimpleGrid cols={{ base: 1, sm: 2, xl: 4 }}>
      <MetricCard title="Top customer" value={data.top_customers[0]?.customer_name || '—'} subtitle={data.top_customers[0] ? `${asMoney(data.top_customers[0].revenue)} net sales` : 'No sales this month'} icon={<IconUsers size={20} />} />
      <MetricCard title="Lowest active customer" value={data.bottom_customers[0]?.customer_name || '—'} subtitle={data.bottom_customers[0] ? `${asMoney(data.bottom_customers[0].revenue)} net sales` : 'No sales this month'} icon={<IconUsers size={20} />} color="orange" />
      <MetricCard title="Expiring ≤ 7 days" value={number.format(data.inventory.expiring_7_days_units)} subtitle={`${data.inventory.expiring_7_days_batch_count} batches`} icon={<IconCalendarDue size={20} />} color="orange" />
      <MetricCard title="Expired stock" value={number.format(data.inventory.expired_units)} subtitle={`${data.inventory.expired_batch_count} batches still on hand`} icon={<IconCalendarDue size={20} />} color="red" />
    </SimpleGrid>
    <SimpleGrid cols={{ base: 1, lg: 2 }}>
      <CustomerList title="Highest-value customers" subtitle="Ranked by net sales for the current month" rows={data.top_customers} empty="No customer sales yet." tone="positive" />
      <CustomerList title="Lowest active customers" subtitle="Customers with sales, ranked by net contribution" rows={data.bottom_customers} empty="No customer sales yet." tone="negative" />
    </SimpleGrid>
    <SimpleGrid cols={{ base: 1, lg: 2 }}>
      <Card className="surface-panel bento-card" radius="xl" p="lg" withBorder><Text fw={800}>Expiring soon</Text><Text size="xs" c="dimmed" mt={2}>FEFO will prefer earlier expiry dates for normal stock issuance.</Text><Stack gap="sm" mt="lg">{expiry.map((row) => <Group key={`${row.batch_id}-${row.location_id}`} justify="space-between" wrap="nowrap"><Group gap="sm" wrap="nowrap" miw={0}><ThemeIcon size={34} radius="md" color={row.days_to_expiry <= 7 ? 'orange' : 'cyan'} variant="light"><IconCalendarDue size={17} /></ThemeIcon><div style={{ minWidth: 0 }}><Text size="sm" fw={700} truncate>{row.product_name}</Text><Text size="xs" c="dimmed">{row.location_name} · batch {row.batch_number || row.batch_id}</Text></div></Group><div style={{ textAlign: 'right' }}><Badge color={row.days_to_expiry <= 7 ? 'orange' : 'cyan'} variant="light">{row.days_to_expiry}d</Badge><Text size="xs" c="dimmed" mt={3}>{row.expiry_date} · qty {number.format(row.quantity)}</Text></div></Group>)}{!expiry.length && <Text size="sm" c="teal">No batches expire within 30 days.</Text>}</Stack></Card>
      <Card className="surface-panel bento-card" radius="xl" p="lg" withBorder><Text fw={800}>Expired stock control</Text><Text size="xs" c="dimmed" mt={2}>Expired batches remain visible for quarantine/write-off decisions and are excluded from normal FEFO picking.</Text><Stack gap="sm" mt="lg">{expired.map((row) => <Group key={`${row.batch_id}-${row.location_id}`} justify="space-between" wrap="nowrap"><Group gap="sm" wrap="nowrap" miw={0}><ThemeIcon size={34} radius="md" color="red" variant="light"><IconCalendarDue size={17} /></ThemeIcon><div style={{ minWidth: 0 }}><Text size="sm" fw={700} truncate>{row.product_name}</Text><Text size="xs" c="dimmed">{row.location_name} · batch {row.batch_number || row.batch_id}</Text></div></Group><div style={{ textAlign: 'right' }}><Badge color="red" variant="light">Expired</Badge><Text size="xs" c="dimmed" mt={3}>{Math.abs(row.days_to_expiry)}d overdue · qty {number.format(row.quantity)}</Text></div></Group>)}{!expired.length && <Text size="sm" c="teal">No expired stock on hand.</Text>}</Stack></Card>
    </SimpleGrid>
    <Card className="surface-panel bento-card" radius="xl" p="lg" withBorder><Group gap="sm"><IconArrowUpRight size={17} /><Text size="sm">Insights are calculated from confirmed sales and current stock balances.</Text><IconArrowDownRight size={17} /></Group></Card>
  </Stack>;
}
