import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { DatePickerInput } from '@mantine/dates';
import { BarChart, DonutChart } from '@mantine/charts';
import {
  Badge,
  Card,
  Group,
  Loader,
  Paper,
  Progress,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { IconArrowDownRight, IconArrowUpRight, IconBox, IconCash, IconChartBar, IconShoppingCart } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';

import { api, query } from '../lib/api';

type SalesData = { gross_sales: number | string; units_sold: number; invoice_count: number };
type PurchaseData = { purchase_value: number | string; units_purchased: number; purchase_count: number };
type InventoryData = { total_units: number; inventory_value: number | string; product_count: number; low_stock_count: number; low_stock: { product_id: number; product_name: string; stock: number }[] };
type TopProduct = { product_id: number; 'product__name': string; quantity: number; revenue: number | string };
type EmployeeSales = { invoice__created_by_id: number; 'invoice__created_by__email': string; quantity: number; revenue: number | string };
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

function StatCard({ label, value, icon, trend, tone = 'indigo' }: { label: string; value: string; icon: ReactNode; trend?: string; tone?: string }) {
  return (
    <Card className="glass bento-card" radius="lg" p="lg" withBorder>
      <Group justify="space-between" align="flex-start">
        <div>
          <Text size="xs" c="dimmed" fw={800} tt="uppercase" lts=".08em">{label}</Text>
          <Text className="kpi-number" fw={900} size="clamp(1.7rem, 3vw, 2.35rem)" mt={6}>{value}</Text>
          {trend && <Group gap={5} mt={4}><IconArrowUpRight size={14} /><Text size="xs" c="teal.4" fw={700}>{trend}</Text></Group>}
        </div>
        <Paper p="sm" radius="md" withBorder bg={`${tone}.9`} c="white">{icon}</Paper>
      </Group>
    </Card>
  );
}

export function DashboardPage() {
  const [range, setRange] = useState<Range>('month');
  const [customFrom, setCustomFrom] = useState<string | null>(null);
  const [customTo, setCustomTo] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sales, setSales] = useState<SalesData | null>(null);
  const [purchases, setPurchases] = useState<PurchaseData | null>(null);
  const [inventory, setInventory] = useState<InventoryData | null>(null);
  const [topProducts, setTopProducts] = useState<TopProduct[]>([]);
  const [employeeSales, setEmployeeSales] = useState<EmployeeSales[]>([]);

  const rangeParams = useMemo(() => getRange(range, customFrom, customTo), [range, customFrom, customTo]);

  const load = useCallback(async () => {
    if (range === 'custom' && (!rangeParams.from || !rangeParams.to)) return;
    setLoading(true);
    try {
      const suffix = query({ from: rangeParams.from, to: rangeParams.to });
      const [salesResult, purchaseResult, inventoryResult, topResult, employeeResult] = await Promise.all([
        api.accounting.salesAnalytics(suffix),
        api.accounting.purchaseAnalytics(suffix),
        api.accounting.inventoryAnalytics(),
        api.accounting.topProducts(query({ from: rangeParams.from, to: rangeParams.to, limit: 6 })),
        api.accounting.salesByEmployee(suffix),
      ]);
      setSales(salesResult as SalesData);
      setPurchases(purchaseResult as PurchaseData);
      setInventory(inventoryResult as InventoryData);
      setTopProducts(((topResult as { products: TopProduct[] }).products || []).slice(0, 6));
      setEmployeeSales(((employeeResult as { employees: EmployeeSales[] }).employees || []).slice(0, 6));
    } catch (error) {
      notifications.show({ title: 'Dashboard unavailable', message: error instanceof Error ? error.message : 'Unable to load dashboard data.', color: 'red' });
    } finally {
      setLoading(false);
    }
  }, [range, rangeParams]);

  useEffect(() => { void load(); }, [load]);

  const chartProducts = topProducts.map((item) => ({ name: item['product__name'], revenue: Number(item.revenue || 0) }));
  const chartEmployees = employeeSales.map((item) => ({ name: item['invoice__created_by__email'] || `Employee ${item.invoice__created_by_id}`, revenue: Number(item.revenue || 0) }));
  const profitEstimate = Number(sales?.gross_sales || 0) - Number(purchases?.purchase_value || 0);

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="flex-end" wrap="wrap">
        <div>
          <Text size="sm" c="indigo.3" fw={800}>OPERATIONS OVERVIEW</Text>
          <Title order={1} mt={4} style={{ letterSpacing: '-0.04em' }}>Good morning, command center.</Title>
          <Text c="dimmed" mt={4}>A live view of sales, purchases, inventory and team performance.</Text>
        </div>
        <SegmentedControl value={range} onChange={(value) => setRange(value as Range)} data={[{ label: 'Today', value: 'today' }, { label: '7 days', value: 'week' }, { label: 'Month', value: 'month' }, { label: 'Year', value: 'year' }, { label: 'Custom', value: 'custom' }]} />
      </Group>

      {range === 'custom' && (
        <Group grow maw={640}>
          <DatePickerInput label="From" value={customFrom} onChange={setCustomFrom} placeholder="Start date" clearable />
          <DatePickerInput label="To" value={customTo} onChange={setCustomTo} placeholder="End date" clearable />
        </Group>
      )}

      {loading && !sales ? (
        <Card className="glass" radius="lg" p={50} withBorder><Group justify="center"><Loader /></Group></Card>
      ) : (
        <>
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
            <StatCard label="Net sales" value={asMoney(sales?.gross_sales)} icon={<IconChartBar size={20} />} trend={`${number.format(sales?.invoice_count || 0)} invoices`} />
            <StatCard label="Gross contribution" value={asMoney(profitEstimate)} icon={<IconCash size={20} />} trend={`${number.format(sales?.units_sold || 0)} units sold`} tone="cyan" />
            <StatCard label="Purchases" value={asMoney(purchases?.purchase_value)} icon={<IconShoppingCart size={20} />} trend={`${number.format(purchases?.purchase_count || 0)} purchases`} tone="violet" />
            <StatCard label="Inventory value" value={asMoney(inventory?.inventory_value)} icon={<IconBox size={20} />} trend={`${number.format(inventory?.total_units || 0)} units`} tone="teal" />
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, lg: 2 }}>
            <Card className="glass bento-card" radius="lg" p="lg" withBorder>
              <Group justify="space-between" mb="md"><div><Text fw={800}>Top products</Text><Text size="xs" c="dimmed">Revenue in the selected period</Text></div><Badge variant="light">Live</Badge></Group>
              {chartProducts.length ? <BarChart h={300} data={chartProducts} dataKey="name" series={[{ name: 'revenue', color: 'indigo.5' }]} tickLine="y" gridAxis="y" /> : <Text c="dimmed" py="xl" ta="center">No sales data for this period.</Text>}
            </Card>

            <Card className="glass bento-card" radius="lg" p="lg" withBorder>
              <Group justify="space-between" mb="md"><div><Text fw={800}>Sales by employee</Text><Text size="xs" c="dimmed">Ranked by revenue</Text></div><Badge variant="light" color="cyan">Team</Badge></Group>
              {chartEmployees.length ? <BarChart h={300} data={chartEmployees} dataKey="name" series={[{ name: 'revenue', color: 'cyan.5' }]} tickLine="y" gridAxis="y" /> : <Text c="dimmed" py="xl" ta="center">No employee sales yet.</Text>}
            </Card>
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, md: 3 }}>
            <Card className="glass bento-card" radius="lg" p="lg" withBorder>
              <Text fw={800}>Inventory health</Text>
              <Text size="xs" c="dimmed">Current stock position</Text>
              <Group align="flex-end" mt="xl"><Text fw={900} size="2.5rem">{number.format(inventory?.product_count || 0)}</Text><Text c="dimmed" pb={8}>active products</Text></Group>
              <Progress value={inventory ? Math.max(8, 100 - ((inventory.low_stock_count / Math.max(inventory.product_count, 1)) * 100)) : 8} mt="md" radius="xl" />
              <Text size="xs" c="dimmed" mt="sm">{number.format(inventory?.low_stock_count || 0)} items need attention</Text>
            </Card>

            <Card className="glass bento-card" radius="lg" p="lg" withBorder>
              <Text fw={800}>Sales vs purchases</Text>
              <Text size="xs" c="dimmed">Selected period</Text>
              <DonutChart mt="md" size={190} thickness={22} data={[{ name: 'Sales', value: Math.max(Number(sales?.gross_sales || 0), 0), color: 'indigo.5' }, { name: 'Purchases', value: Math.max(Number(purchases?.purchase_value || 0), 0), color: 'violet.5' }]} withTooltip />
            </Card>

            <Card className="glass bento-card" radius="lg" p="lg" withBorder>
              <Group justify="space-between"><div><Text fw={800}>Low stock</Text><Text size="xs" c="dimmed">Threshold-driven alerts</Text></div><IconArrowDownRight size={18} /></Group>
              <Stack mt="md" gap="sm">
                {(inventory?.low_stock || []).slice(0, 5).map((item) => (
                  <div key={item.product_id}><Group justify="space-between" mb={4}><Text size="sm">{item.product_name}</Text><Badge size="sm" color="red" variant="light">{item.stock}</Badge></Group><Progress value={Math.min(item.stock * 10, 100)} size="xs" color="red" radius="xl" /></div>
                ))}
                {!inventory?.low_stock?.length && <Text c="teal.4" size="sm">Inventory is healthy.</Text>}
              </Stack>
            </Card>
          </SimpleGrid>
        </>
      )}
    </Stack>
  );
}
