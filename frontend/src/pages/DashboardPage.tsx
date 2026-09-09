import { Link } from 'react-router-dom';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { AreaChart } from '@mantine/charts';
import { Badge, Button, Card, Group, Loader, Progress, SegmentedControl, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { notifications } from '@mantine/notifications';

import { api, query, type DashboardOverview } from '../lib/api';

type Range = 'today' | 'week' | 'month' | 'year' | 'custom';

const money = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const number = new Intl.NumberFormat('en-US');

function asMoney(value: unknown) {
  const amount = Number(value || 0);
  return money.format(Number.isFinite(amount) ? amount : 0);
}

function isoDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function getRange(range: Range, customFrom: string | null, customTo: string | null) {
  const today = isoDate(new Date());
  if (range === 'custom') return { from: customFrom || undefined, to: customTo || undefined };
  if (range === 'today') return { from: today, to: today };
  const from = new Date();
  if (range === 'week') from.setDate(from.getDate() - 6);
  if (range === 'month') from.setDate(1);
  if (range === 'year') from.setMonth(0, 1);
  return { from: isoDate(from), to: today };
}

function Metric({ label, value, meta }: { label: string; value: string; meta: string }) {
  return (
    <div className="dashboard-metric">
      <Text size="xs" c="dimmed" fw={700}>{label}</Text>
      <Text className="kpi-number" fw={900} size="clamp(1.45rem, 2.4vw, 2rem)" mt={5}>{value}</Text>
      <Text size="xs" c="dimmed" mt={3}>{meta}</Text>
    </div>
  );
}

function Panel({ title, subtitle, right, children }: { title: string; subtitle?: string; right?: React.ReactNode; children: React.ReactNode }) {
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

function RiskRow({ label, count, units, color, to }: { label: string; count: unknown; units?: unknown; color: string; to: string }) {
  const numericCount = Number(count || 0);
  return (
    <Group className="dashboard-risk-row" justify="space-between" wrap="nowrap" gap="md">
      <div style={{ minWidth: 0 }}>
        <Text fw={700} size="sm">{label}</Text>
        <Text size="xs" c="dimmed" mt={2}>{number.format(Number(units || 0))} units affected</Text>
      </div>
      <Group gap="sm" wrap="nowrap">
        <Badge color={color} variant="light">{number.format(numericCount)}</Badge>
        <Button component={Link} to={to} variant="subtle" size="compact-sm">Open</Button>
      </Group>
    </Group>
  );
}

export function DashboardPage() {
  const [range, setRange] = useState<Range>('month');
  const [customFrom, setCustomFrom] = useState<string | null>(null);
  const [customTo, setCustomTo] = useState<string | null>(null);
  const [rangeError, setRangeError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DashboardOverview | null>(null);

  const rangeParams = useMemo(() => getRange(range, customFrom, customTo), [range, customFrom, customTo]);

  const load = useCallback(async () => {
    if (range === 'custom') {
      if (!rangeParams.from || !rangeParams.to) {
        setRangeError('Choose both dates to view this range.');
        setLoading(false);
        return;
      }
      if (rangeParams.from > rangeParams.to) {
        setRangeError('The start date must be on or before the end date.');
        setLoading(false);
        return;
      }
    }

    setRangeError(null);
    setLoading(true);
    try {
      setData(await api.accounting.dashboardOverview(query({ from: rangeParams.from, to: rangeParams.to })));
    } catch (error) {
      notifications.show({
        title: 'Dashboard unavailable',
        message: error instanceof Error ? error.message : 'Unable to load dashboard data.',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  }, [range, rangeParams]);

  useEffect(() => { void load(); }, [load]);

  const receivables = useMemo(
    () => (data?.customer_balances || []).reduce((sum, row) => sum + Number(row.balance || 0), 0),
    [data],
  );
  const payables = useMemo(
    () => (data?.supplier_balances || []).reduce((sum, row) => sum + Number(row.balance || 0), 0),
    [data],
  );
  const trend = useMemo(() => {
    const values = new Map<string, { date: string; sales: number; purchases: number }>();
    (data?.sales.trend || []).forEach((row) => values.set(row.date, {
      date: row.date,
      sales: Number(row.value || 0),
      purchases: values.get(row.date)?.purchases || 0,
    }));
    (data?.purchases.trend || []).forEach((row) => values.set(row.date, {
      date: row.date,
      sales: values.get(row.date)?.sales || 0,
      purchases: Number(row.value || 0),
    }));
    return Array.from(values.values()).sort((a, b) => a.date.localeCompare(b.date));
  }, [data]);
  const expiryRisks = useMemo(
    () => [
      ...(data?.inventory.expired_alerts || []),
      ...(data?.inventory.expiry_alerts || []),
    ]
      .sort((a, b) => Number(a.days_to_expiry) - Number(b.days_to_expiry))
      .slice(0, 4),
    [data],
  );

  const inventoryCoverage = Math.max(
    0,
    Math.min(100, 100 - (Number(data?.inventory.low_stock_count || 0) / Math.max(Number(data?.inventory.product_count || 0), 1)) * 100),
  );

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-end" wrap="wrap" gap="md">
        <div>
          <Text size="sm" c="erp.6" fw={800} tt="uppercase" lts=".07em">Executive overview</Text>
          <Title order={1} mt={4} style={{ letterSpacing: '-0.035em' }}>Dashboard</Title>
          <Text c="dimmed" mt={4}>A focused view of performance, liquidity and issues that need attention.</Text>
        </div>
        <Group gap="xs" wrap="wrap">
          <SegmentedControl
            value={range}
            onChange={(value) => setRange(value as Range)}
            data={[
              { label: 'Today', value: 'today' },
              { label: '7 days', value: 'week' },
              { label: 'Month', value: 'month' },
              { label: 'Year', value: 'year' },
              { label: 'Custom', value: 'custom' },
            ]}
          />
          <Button component={Link} to="/insights" variant="subtle" size="sm">Insights</Button>
        </Group>
      </Group>

      {range === 'custom' && (
        <Card className="surface-panel" radius="md" p="md" withBorder>
          <Group grow maw={700} align="flex-end">
            <DatePickerInput label="From" value={customFrom} onChange={setCustomFrom} placeholder="Start date" clearable />
            <DatePickerInput label="To" value={customTo} onChange={setCustomTo} placeholder="End date" clearable />
          </Group>
          {rangeError && <Text size="sm" c="red" mt="xs">{rangeError}</Text>}
        </Card>
      )}

      {loading && !data ? (
        <Card className="surface-panel" radius="lg" p={52} withBorder>
          <Group justify="center"><Loader size="sm" /></Group>
        </Card>
      ) : data ? (
        <>
          <Card className="surface-panel dashboard-metrics" radius="lg" p={0} withBorder>
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing={0}>
              <Metric label="Net sales" value={asMoney(data.sales.gross_sales)} meta={`${number.format(data.sales.invoice_count)} invoices`} />
              <Metric label="Net income" value={asMoney(data.pnl.net_income)} meta={`${asMoney(data.pnl.total_expenses)} expenses`} />
              <Metric label="Cash & bank" value={asMoney(data.cash_flow.ending_cash)} meta={`${asMoney(data.cash_flow.net_change)} net change`} />
              <Metric label="Inventory value" value={asMoney(data.inventory.inventory_value)} meta={`${number.format(data.inventory.total_units)} units`} />
            </SimpleGrid>
          </Card>

          <SimpleGrid cols={{ base: 1, lg: 3 }} spacing="lg">
            <div style={{ gridColumn: 'span 2' }}>
              <Panel title="Sales vs purchases" subtitle="Daily values for the selected period" right={loading ? <Badge variant="light">Updating</Badge> : undefined}>
                {trend.length ? (
                  <AreaChart
                    h={330}
                    data={trend}
                    dataKey="date"
                    curveType="monotone"
                    withLegend
                    legendProps={{ verticalAlign: 'bottom' }}
                    valueFormatter={(value) => asMoney(value)}
                    series={[
                      { name: 'sales', label: 'Sales', color: 'erp.6' },
                      { name: 'purchases', label: 'Purchases', color: 'teal.5' },
                    ]}
                  />
                ) : <Text c="dimmed" ta="center" py={110}>No activity in this period.</Text>}
              </Panel>
            </div>

            <Panel title="Needs attention" subtitle="Only issues that may require action">
              <Stack gap={0}>
                <RiskRow label="Expired batches" count={data.inventory.expired_batch_count} units={data.inventory.expired_units} color="red" to="/inventory/batches" />
                <RiskRow label="Expiring within 7 days" count={data.inventory.expiring_7_days_batch_count} units={data.inventory.expiring_7_days_units} color="orange" to="/inventory/batches" />
                <RiskRow label="Low stock products" count={data.inventory.low_stock_count} units={data.inventory.total_units} color={data.inventory.low_stock_count ? 'orange' : 'teal'} to="/inventory" />
              </Stack>
            </Panel>
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="lg">
            <Panel title="Working capital" subtitle="Open balances and available cash">
              <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg">
                <div><Text size="xs" c="dimmed">Receivables</Text><Text fw={850} mt={4}>{asMoney(receivables)}</Text></div>
                <div><Text size="xs" c="dimmed">Payables</Text><Text fw={850} mt={4}>{asMoney(payables)}</Text></div>
                <div><Text size="xs" c="dimmed">Cash</Text><Text fw={850} mt={4}>{asMoney(data.cash_flow.ending_cash)}</Text></div>
              </SimpleGrid>
            </Panel>

            <Panel title="Inventory health" subtitle="Current stock position" right={<Button component={Link} to="/inventory/batches" variant="subtle" size="compact-sm">View batches</Button>}>
              <Group justify="space-between" align="flex-end">
                <div>
                  <Text size="xs" c="dimmed">Active products</Text>
                  <Text fw={900} size="2rem" mt={4}>{number.format(data.inventory.product_count)}</Text>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <Text size="xs" c="dimmed">Low stock</Text>
                  <Text fw={800} mt={4}>{number.format(data.inventory.low_stock_count)}</Text>
                </div>
              </Group>
              <Progress value={inventoryCoverage} mt="lg" radius="xl" color={data.inventory.low_stock_count ? 'orange' : 'teal'} />
              <Text size="xs" c="dimmed" mt="sm">{number.format(data.inventory.total_units)} units on hand · threshold {number.format(data.inventory.low_stock_threshold || 10)}</Text>
            </Panel>
          </SimpleGrid>

          <Panel title="Expiry watch" subtitle="Expired and upcoming batches, ordered by urgency" right={<Button component={Link} to="/inventory/batches" variant="subtle" size="compact-sm">View all</Button>}>
            {expiryRisks.length ? (
              <Stack gap="xs">
                {expiryRisks.map((item) => {
                  const days = Number(item.days_to_expiry);
                  const expired = days < 0;
                  const today = days === 0;
                  const label = expired ? 'Expired' : today ? 'Today' : `${days}d left`;
                  const color = expired ? 'red' : days <= 7 ? 'orange' : days <= 30 ? 'yellow' : 'teal';
                  return (
                    <Group key={`${item.batch_id}-${item.location_id}`} className="dashboard-expiry-row" justify="space-between" wrap="nowrap">
                      <div style={{ minWidth: 0 }}>
                        <Text size="sm" fw={700} truncate>{item.product_name}</Text>
                        <Text size="xs" c="dimmed" mt={2} truncate>{item.location_name} · {item.batch_number || `Batch #${item.batch_id}`}</Text>
                      </div>
                      <Group gap="sm" wrap="nowrap">
                        <Text size="xs" c="dimmed">{number.format(Number(item.quantity || 0))} units</Text>
                        <Badge color={color} variant="light">{label}</Badge>
                      </Group>
                    </Group>
                  );
                })}
              </Stack>
            ) : (
              <Text size="sm" c="teal.5">No expired or upcoming batches need attention.</Text>
            )}
          </Panel>
        </>
      ) : null}
    </Stack>
  );
}
