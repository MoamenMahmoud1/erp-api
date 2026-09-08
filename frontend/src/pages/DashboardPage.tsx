import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { AreaChart, BarChart } from '@mantine/charts';
import { Badge, Card, Group, Loader, Progress, SegmentedControl, SimpleGrid, Stack, Text, ThemeIcon, Title } from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { IconArrowDownRight, IconArrowUpRight, IconBox, IconCash, IconChartLine, IconReceipt, IconShoppingCart, IconUsers } from '@tabler/icons-react';
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
  const now = new Date();
  const today = isoDate(now);
  if (range === 'custom') return { from: customFrom || undefined, to: customTo || undefined };
  if (range === 'today') return { from: today, to: today };
  const from = new Date(now);
  if (range === 'week') from.setDate(now.getDate() - 6);
  if (range === 'month') from.setDate(1);
  if (range === 'year') from.setMonth(0, 1);
  return { from: isoDate(from), to: today };
}

function StatCard({ label, value, meta, icon, tone }: { label: string; value: string; meta: string; icon: ReactNode; tone: string }) {
  return (
    <Card className="surface-panel bento-card" radius="xl" p="lg" withBorder>
      <Group justify="space-between" align="flex-start">
        <div>
          <Text size="xs" c="dimmed" fw={800} tt="uppercase" lts=".08em">{label}</Text>
          <Text className="kpi-number" fw={900} size="clamp(1.55rem, 2.6vw, 2.15rem)" mt={7}>{value}</Text>
          <Text size="xs" c="dimmed" mt={5}>{meta}</Text>
        </div>
        <ThemeIcon size={42} radius="lg" variant="light" color={tone}>{icon}</ThemeIcon>
      </Group>
    </Card>
  );
}

function Panel({ title, subtitle, children, right }: { title: string; subtitle?: string; children: ReactNode; right?: ReactNode }) {
  return (
    <Card className="surface-panel bento-card" radius="xl" p="lg" withBorder>
      <Group justify="space-between" align="flex-start" mb="md">
        <div>
          <Text fw={800}>{title}</Text>
          {subtitle && <Text size="xs" c="dimmed" mt={2}>{subtitle}</Text>}
        </div>
        {right}
      </Group>
      {children}
    </Card>
  );
}

export function DashboardPage() {
  const [range, setRange] = useState<Range>('month');
  const [customFrom, setCustomFrom] = useState<string | null>(null);
  const [customTo, setCustomTo] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DashboardOverview | null>(null);
  const rangeParams = useMemo(() => getRange(range, customFrom, customTo), [range, customFrom, customTo]);

  const load = useCallback(async () => {
    if (range === 'custom' && (!rangeParams.from || !rangeParams.to)) return;
    setLoading(true);
    try {
      setData(await api.accounting.dashboardOverview(query({ from: rangeParams.from, to: rangeParams.to })));
    } catch (error) {
      notifications.show({ title: 'Dashboard unavailable', message: error instanceof Error ? error.message : 'Unable to load dashboard data.', color: 'red' });
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
    (data?.sales.trend || []).forEach((row) => {
      values.set(row.date, { date: row.date, sales: Number(row.value || 0), purchases: values.get(row.date)?.purchases || 0 });
    });
    (data?.purchases.trend || []).forEach((row) => {
      values.set(row.date, { date: row.date, sales: values.get(row.date)?.sales || 0, purchases: Number(row.value || 0) });
    });
    return Array.from(values.values()).sort((a, b) => a.date.localeCompare(b.date));
  }, [data]);

  const topProducts = useMemo(
    () => (data?.top_products || []).map((item) => ({ name: item['product__name'], revenue: Number(item.revenue || 0) })),
    [data],
  );
  const employeeSales = useMemo(
    () => (data?.sales_by_employee || []).slice(0, 6).map((item) => ({ name: item.employee_name, revenue: Number(item.revenue || 0) })),
    [data],
  );
  const topReceivables = useMemo(
    () => [...(data?.customer_balances || [])].filter((row) => Number(row.balance || 0) > 0).sort((a, b) => Number(b.balance) - Number(a.balance)).slice(0, 4),
    [data],
  );
  const topPayables = useMemo(
    () => [...(data?.supplier_balances || [])].filter((row) => Number(row.balance || 0) > 0).sort((a, b) => Number(b.balance) - Number(a.balance)).slice(0, 4),
    [data],
  );

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="flex-end" wrap="wrap">
        <div>
          <Text size="sm" c="indigo.3" fw={800} tt="uppercase" lts=".08em">Executive overview</Text>
          <Title order={1} mt={4} style={{ letterSpacing: '-0.04em' }}>Command center</Title>
          <Text c="dimmed" mt={4}>Sales, cash, working capital and inventory in one view.</Text>
        </div>
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
      </Group>

      {range === 'custom' && (
        <Group grow maw={640}>
          <DatePickerInput label="From" value={customFrom} onChange={setCustomFrom} placeholder="Start date" clearable />
          <DatePickerInput label="To" value={customTo} onChange={setCustomTo} placeholder="End date" clearable />
        </Group>
      )}

      {loading && !data ? (
        <Card className="surface-panel" radius="xl" p={56} withBorder>
          <Group justify="center"><Loader size="sm" /></Group>
        </Card>
      ) : data ? (
        <>
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3, xl: 6 }}>
            <StatCard label="Net sales" value={asMoney(data.sales.gross_sales)} meta={`${number.format(data.sales.invoice_count)} invoices`} icon={<IconChartLine size={20} />} tone="indigo" />
            <StatCard label="Net income" value={asMoney(data.pnl.net_income)} meta={`${asMoney(data.pnl.total_expenses)} expenses`} icon={<IconCash size={20} />} tone="teal" />
            <StatCard label="Cash & bank" value={asMoney(data.cash_flow.ending_cash)} meta={`${asMoney(data.cash_flow.net_change)} net change`} icon={<IconCash size={20} />} tone="cyan" />
            <StatCard label="Receivables" value={asMoney(receivables)} meta="Customer balances" icon={<IconUsers size={20} />} tone="orange" />
            <StatCard label="Payables" value={asMoney(payables)} meta="Supplier balances" icon={<IconReceipt size={20} />} tone="violet" />
            <StatCard label="Inventory" value={asMoney(data.inventory.inventory_value)} meta={`${number.format(data.inventory.total_units)} units`} icon={<IconBox size={20} />} tone="blue" />
          </SimpleGrid>

          <Panel title="Sales vs purchases" subtitle="Daily values for the selected period" right={<Badge variant="light">Live</Badge>}>
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
                  { name: 'sales', label: 'Sales', color: 'indigo.6' },
                  { name: 'purchases', label: 'Purchases', color: 'violet.5' },
                ]}
              />
            ) : <Text c="dimmed" ta="center" py={100}>No activity in this period.</Text>}
          </Panel>

          <SimpleGrid cols={{ base: 1, lg: 2 }}>
            <Panel title="Top products" subtitle="Highest gross product revenue">
              {topProducts.length ? (
                <BarChart
                  h={320}
                  data={topProducts}
                  dataKey="name"
                  orientation="vertical"
                  yAxisProps={{ width: 190 }}
                  barProps={{ radius: 8 }}
                  valueFormatter={(value) => asMoney(value)}
                  series={[{ name: 'revenue', label: 'Revenue', color: 'indigo.6' }]}
                />
              ) : <Text c="dimmed" ta="center" py={100}>No product sales in this period.</Text>}
            </Panel>
            <Panel title="Sales by employee" subtitle="Highest gross sales contribution">
              {employeeSales.length ? (
                <BarChart
                  h={320}
                  data={employeeSales}
                  dataKey="name"
                  orientation="vertical"
                  yAxisProps={{ width: 150 }}
                  barProps={{ radius: 8 }}
                  valueFormatter={(value) => asMoney(value)}
                  series={[{ name: 'revenue', label: 'Revenue', color: 'cyan.6' }]}
                />
              ) : <Text c="dimmed" ta="center" py={100}>No employee sales in this period.</Text>}
            </Panel>
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, md: 2, xl: 4 }}>
            <Panel title="Inventory health" subtitle="Current stock position">
              <Group justify="space-between" align="flex-end" mt="sm">
                <div>
                  <Text fw={900} size="2.2rem">{number.format(data.inventory.product_count)}</Text>
                  <Text size="xs" c="dimmed">active products</Text>
                </div>
                <Badge color={data.inventory.low_stock_count ? 'orange' : 'teal'} variant="light">
                  {number.format(data.inventory.low_stock_count)} low stock
                </Badge>
              </Group>
              <Progress value={Math.max(4, 100 - (data.inventory.low_stock_count / Math.max(data.inventory.product_count, 1)) * 100)} mt="lg" radius="xl" />
              <Text size="xs" c="dimmed" mt="sm">Threshold: {number.format(data.inventory.low_stock_threshold || 10)} units</Text>
            </Panel>

            <Panel title="Cash movement" subtitle="Selected period">
              <Group justify="space-between" mt="sm">
                <div><Text size="xs" c="dimmed">Inflows</Text><Text fw={800} mt={3}>{asMoney(data.cash_flow.total_inflows)}</Text></div>
                <div style={{ textAlign: 'right' }}><Text size="xs" c="dimmed">Outflows</Text><Text fw={800} mt={3}>{asMoney(data.cash_flow.total_outflows)}</Text></div>
              </Group>
              <Group gap={6} mt="lg">
                {Number(data.cash_flow.net_change || 0) >= 0 ? <IconArrowUpRight size={15} /> : <IconArrowDownRight size={15} />}
                <Text size="sm" fw={800}>Net change {asMoney(data.cash_flow.net_change)}</Text>
              </Group>
            </Panel>

            <Panel title="Largest receivables" subtitle="Customers with open balances">
              <Stack gap="sm">
                {topReceivables.map((row) => (
                  <Group key={row.customer_id} justify="space-between" wrap="nowrap">
                    <Text size="sm" truncate>{row.customer_name}</Text>
                    <Text size="sm" fw={800}>{asMoney(row.balance)}</Text>
                  </Group>
                ))}
                {!topReceivables.length && <Text size="sm" c="teal.4">No outstanding receivables.</Text>}
              </Stack>
            </Panel>

            <Panel title="Largest payables" subtitle="Suppliers with open balances">
              <Stack gap="sm">
                {topPayables.map((row) => (
                  <Group key={row.supplier_id} justify="space-between" wrap="nowrap">
                    <Text size="sm" truncate>{row.supplier_name}</Text>
                    <Text size="sm" fw={800}>{asMoney(row.balance)}</Text>
                  </Group>
                ))}
                {!topPayables.length && <Text size="sm" c="teal.4">No outstanding payables.</Text>}
              </Stack>
            </Panel>
          </SimpleGrid>

          <Panel title="Low stock" subtitle="Products that need replenishment">
            <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
              {(data.inventory.low_stock || []).slice(0, 6).map((item) => (
                <Card key={item.product_id} withBorder radius="lg" p="sm" bg="transparent">
                  <Group justify="space-between" wrap="nowrap">
                    <Group gap="sm" wrap="nowrap">
                      <ThemeIcon size={34} radius="md" color="orange" variant="light"><IconShoppingCart size={16} /></ThemeIcon>
                      <Text size="sm" fw={700} truncate>{item.product_name}</Text>
                    </Group>
                    <Badge color="orange" variant="light">{item.stock}</Badge>
                  </Group>
                </Card>
              ))}
            </SimpleGrid>
            {!data.inventory.low_stock?.length && <Text size="sm" c="teal.4">Inventory is healthy.</Text>}
          </Panel>
        </>
      ) : null}
    </Stack>
  );
}
