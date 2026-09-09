import type { ReactNode } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { Badge, Button, Card, Group, Loader, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { Link } from 'react-router-dom';
import { notifications } from '@mantine/notifications';

import { api, query, type DashboardOverview } from '../lib/api';

const money = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const number = new Intl.NumberFormat('en-US');
const asMoney = (value: unknown) => money.format(Number(value || 0));
const isoLocal = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;

function Section({ title, subtitle, right, children }: { title: string; subtitle?: string; right?: ReactNode; children: ReactNode }) {
  return (
    <Card className="surface-panel bento-card" radius="lg" p="lg" withBorder>
      <Group justify="space-between" align="flex-start" gap="md" mb="md">
        <div>
          <Text fw={800}>{title}</Text>
          {subtitle && <Text size="xs" c="dimmed" mt={3}>{subtitle}</Text>}
        </div>
        {right}
      </Group>
      {children}
    </Card>
  );
}

function Ranking({ rows, empty }: { rows: DashboardOverview['top_customers']; empty: string }) {
  if (!rows.length) return <Text size="sm" c="dimmed">{empty}</Text>;
  return (
    <Stack gap={0}>
      {rows.slice(0, 8).map((row, index) => (
        <Group key={row.customer_id} className="dashboard-expiry-row" justify="space-between" wrap="nowrap" gap="md">
          <Group gap="sm" wrap="nowrap" miw={0}>
            <Text size="sm" c="dimmed" w={20}>{index + 1}</Text>
            <div style={{ minWidth: 0 }}>
              <Text size="sm" fw={700} truncate>{row.customer_name}</Text>
              <Text size="xs" c="dimmed" mt={2}>{row.invoice_count} invoices · {number.format(row.units_sold)} units</Text>
            </div>
          </Group>
          <div style={{ textAlign: 'right' }}>
            <Text size="sm" fw={850}>{asMoney(row.revenue)}</Text>
            <Text size="xs" c={row.returns ? 'orange' : 'dimmed'} mt={2}>{row.returns ? `Returns ${asMoney(row.returns)}` : 'No returns'}</Text>
          </div>
        </Group>
      ))}
    </Stack>
  );
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

  const expiry = useMemo(() => [
    ...(data?.inventory.expired_alerts || []),
    ...(data?.inventory.expiry_alerts || []),
  ].sort((a, b) => Number(a.days_to_expiry) - Number(b.days_to_expiry)).slice(0, 8), [data]);

  if (loading && !data) return <Group justify="center" mih="50vh"><Loader size="sm" /></Group>;
  if (!data) return <Text c="dimmed">No insight data available.</Text>;

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-end" wrap="wrap" gap="md">
        <div>
          <Text size="sm" c="erp.6" fw={800} tt="uppercase" lts=".07em">Intelligence</Text>
          <Title order={1} mt={4}>Business insights</Title>
          <Text c="dimmed" mt={4}>Detailed rankings and inventory risks for the current month.</Text>
        </div>
        <Button component={Link} to="/inventory/batches" variant="subtle" size="sm">Inventory risks</Button>
      </Group>

      <Card className="surface-panel dashboard-metrics" radius="lg" p={0} withBorder>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing={0}>
          <div className="dashboard-metric"><Text size="xs" c="dimmed">Top customer</Text><Text fw={850} mt={5} truncate>{data.top_customers[0]?.customer_name || '—'}</Text><Text size="xs" c="dimmed" mt={3}>{data.top_customers[0] ? asMoney(data.top_customers[0].revenue) : 'No sales'}</Text></div>
          <div className="dashboard-metric"><Text size="xs" c="dimmed">Lowest active customer</Text><Text fw={850} mt={5} truncate>{data.bottom_customers[0]?.customer_name || '—'}</Text><Text size="xs" c="dimmed" mt={3}>{data.bottom_customers[0] ? asMoney(data.bottom_customers[0].revenue) : 'No sales'}</Text></div>
          <div className="dashboard-metric"><Text size="xs" c="dimmed">Expiring within 7 days</Text><Text fw={900} mt={5}>{number.format(data.inventory.expiring_7_days_units)} units</Text><Text size="xs" c="dimmed" mt={3}>{number.format(data.inventory.expiring_7_days_batch_count)} batches</Text></div>
          <div className="dashboard-metric"><Text size="xs" c="dimmed">Expired stock</Text><Text fw={900} mt={5}>{number.format(data.inventory.expired_units)} units</Text><Text size="xs" c="dimmed" mt={3}>{number.format(data.inventory.expired_batch_count)} batches</Text></div>
        </SimpleGrid>
      </Card>

      <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="lg">
        <Section title="Highest-value customers" subtitle="Ranked by net sales for the current month">
          <Ranking rows={data.top_customers} empty="No customer sales yet." />
        </Section>
        <Section title="Lowest active customers" subtitle="Customers with sales, ranked by net contribution">
          <Ranking rows={data.bottom_customers} empty="No customer sales yet." />
        </Section>
      </SimpleGrid>

      <Section title="Expiry watch" subtitle="Expired and upcoming batches ordered by urgency" right={<Button component={Link} to="/inventory/batches" variant="subtle" size="compact-sm">View all</Button>}>
        {expiry.length ? (
          <Stack gap={0}>
            {expiry.map((row) => {
              const days = Number(row.days_to_expiry);
              const expired = days < 0;
              const today = days === 0;
              return (
                <Group key={`${row.batch_id}-${row.location_id}`} className="dashboard-expiry-row" justify="space-between" wrap="nowrap" gap="md">
                  <div style={{ minWidth: 0 }}>
                    <Text size="sm" fw={700} truncate>{row.product_name}</Text>
                    <Text size="xs" c="dimmed" mt={2} truncate>{row.location_name} · batch {row.batch_number || row.batch_id}</Text>
                  </div>
                  <Group gap="sm" wrap="nowrap">
                    <Text size="xs" c="dimmed">{number.format(Number(row.quantity || 0))} units</Text>
                    <Badge color={expired ? 'red' : days <= 7 ? 'orange' : days <= 30 ? 'yellow' : 'teal'} variant="light">
                      {expired ? `${Math.abs(days)}d overdue` : today ? 'Expires today' : `${days}d left`}
                    </Badge>
                  </Group>
                </Group>
              );
            })}
          </Stack>
        ) : <Text size="sm" c="teal.5">No expired or upcoming batches need attention.</Text>}
      </Section>
    </Stack>
  );
}
