import { useEffect, useMemo, useState } from 'react';
import { DatePickerInput } from '@mantine/dates';
import { Badge, Button, Card, Group, Loader, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { Link } from 'react-router-dom';

import { CrudPage, type CrudOption } from '../components/CrudPage';
import { RecordsPage } from '../components/RecordsPage';
import { api, query, type Paginated } from '../lib/api';

const money = (value: unknown) => Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const accountTypeOptions = [{ value: 'asset', label: 'Asset' }, { value: 'liability', label: 'Liability' }, { value: 'equity', label: 'Equity' }, { value: 'revenue', label: 'Revenue' }, { value: 'expense', label: 'Expense' }];

export function AccountingHomePage() {
  const [loading, setLoading] = useState(true);
  const [pnl, setPnl] = useState<Record<string, unknown> | null>(null);
  const [bs, setBs] = useState<Record<string, unknown> | null>(null);
  useEffect(() => {
    const asOf = new Date().toISOString().slice(0, 10);
    Promise.all([api.accounting.profitAndLoss(), api.accounting.balanceSheet(query({ as_of: asOf }))])
      .then(([profit, balance]) => { setPnl(profit as Record<string, unknown>); setBs(balance as Record<string, unknown>); })
      .catch((error) => notifications.show({ title: 'Accounting unavailable', message: error instanceof Error ? error.message : 'Request failed', color: 'red' }))
      .finally(() => setLoading(false));
  }, []);
  if (loading) return <Card className="glass" radius="lg" p={60} withBorder><Group justify="center"><Loader /></Group></Card>;
  return <Stack gap="xl"><div><Text size="sm" c="indigo.3" fw={800}>ACCOUNTING</Text><Title order={1} mt={4}>Financial command center</Title><Text c="dimmed" mt={4}>The accounting layer is driven by posted journals and business transactions.</Text></div><SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}><Card className="glass bento-card" radius="lg" withBorder><Text c="dimmed" size="xs" tt="uppercase" fw={800}>Revenue</Text><Text fw={900} size="2rem" mt={6}>{money(pnl?.total_revenue)}</Text></Card><Card className="glass bento-card" radius="lg" withBorder><Text c="dimmed" size="xs" tt="uppercase" fw={800}>Expenses</Text><Text fw={900} size="2rem" mt={6}>{money(pnl?.total_expenses)}</Text></Card><Card className="glass bento-card" radius="lg" withBorder><Text c="dimmed" size="xs" tt="uppercase" fw={800}>Net income</Text><Text fw={900} size="2rem" mt={6}>{money(pnl?.net_income)}</Text></Card><Card className="glass bento-card" radius="lg" withBorder><Group justify="space-between"><div><Text c="dimmed" size="xs" tt="uppercase" fw={800}>Assets</Text><Text fw={900} size="2rem" mt={6}>{money(bs?.total_assets)}</Text></div><Badge color={bs?.balanced ? 'teal' : 'red'}>{bs?.balanced ? 'Balanced' : 'Check'}</Badge></Group></Card></SimpleGrid></Stack>;
}

type AccountOptions = { accounts: Paginated };

export function AccountsPage() {
  const [data, setData] = useState<AccountOptions | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.accounting.accounts('?page_size=50')
      .then((accounts) => setData({ accounts }))
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : 'Unable to load account options.'));
  }, []);

  const options = useMemo<CrudOption[]>(() => (data?.accounts.results || []).map((account) => ({
    value: String(account.id),
    label: `${account.code || 'No code'} · ${account.name || 'Unnamed account'}`,
  })), [data]);

  if (error) return <Card className="glass" radius="xl" p="xl" withBorder><Text fw={800}>Accounts unavailable</Text><Text c="dimmed" mt="xs">{error}</Text></Card>;
  if (!data) return <Card className="glass" radius="xl" p={56} withBorder><Group justify="center"><Loader size="sm" /></Group><Text ta="center" size="sm" c="dimmed" mt="md">Loading account hierarchy…</Text></Card>;

  return <CrudPage title="Accounts" singularTitle="Account" subtitle="Chart of accounts used by the posting engine and reports." list={api.accounting.accounts} create={api.accounting.createAccount} update={api.accounting.updateAccount} remove={api.accounting.deleteAccount} fields={[{ key: 'code', label: 'Code', required: true }, { key: 'name', label: 'Name', required: true }, { key: 'account_type', label: 'Account type', type: 'select', options: accountTypeOptions, required: true }, { key: 'parent', label: 'Parent account', type: 'select', options, clearable: true }, { key: 'is_active', label: 'Active', type: 'boolean' }]} columns={[{ key: 'code', label: 'Code' }, { key: 'name', label: 'Account' }, { key: 'account_type', label: 'Type' }, { key: 'normal_side', label: 'Normal side' }, { key: 'is_active', label: 'Status' }]} />;
}

function JournalDetails({ data }: { data: Record<string, unknown> }) {
  const lines = Array.isArray(data.lines) ? data.lines as Record<string, unknown>[] : [];
  const status = String(data.status || '');
  const sourceId = data.source_entity_id == null ? null : Number(data.source_entity_id);
  const sourceType = String(data.source_entity_type || '');
  const sourceLabel = String(data.source_label || '');
  const sourceText = data.source_id == null ? sourceLabel || 'Manual journal' : `${sourceLabel || 'Source'} #${String(data.source_id)}`;
  const sourcePath = sourceId === null
    ? null
    : sourceType === 'invoice'
      ? `/sales/${sourceId}`
      : sourceType === 'purchase'
        ? `/purchases/${sourceId}`
        : null;

  return <Stack gap="lg"><SimpleGrid cols={{ base: 1, sm: 2 }}><Card withBorder radius="lg"><Text size="xs" c="dimmed">ENTRY</Text><Text fw={900} size="xl">{String(data.number || '—')}</Text><Text size="sm" c="dimmed" mt="xs">{String(data.entry_date || '—')}</Text></Card><Card withBorder radius="lg"><Text size="xs" c="dimmed">STATUS</Text><Badge mt="xs" color={status === 'posted' ? 'teal' : 'yellow'} size="lg">{status || '—'}</Badge><Text size="sm" c="dimmed" mt="sm">Reference: {String(data.reference || '—')}</Text></Card></SimpleGrid><Card withBorder radius="lg"><Group justify="space-between" align="flex-start" wrap="wrap"><div><Text fw={800}>{String(data.description || 'Journal entry')}</Text><Text size="sm" c="dimmed" mt={4}>{lines.length} line{lines.length === 1 ? '' : 's'}</Text></div><div><Text size="xs" c="dimmed">SOURCE</Text>{sourcePath ? <Button component={Link} to={sourcePath} variant="subtle" px={0}>{sourceText}</Button> : <Text fw={800} mt={3}>{sourceText}</Text>}</div></Group><Group gap="lg" mt="md"><div><Text size="xs" c="dimmed">Created by</Text><Text fw={700} mt={2}>{String(data.created_by_name || data.created_by_username || '—')}</Text></div><div><Text size="xs" c="dimmed">Posted by</Text><Text fw={700} mt={2}>{String(data.posted_by_name || data.posted_by_username || '—')}</Text></div></Group><Table.ScrollContainer minWidth={620} mt="md"><Table highlightOnHover><Table.Thead><Table.Tr><Table.Th>Account</Table.Th><Table.Th>Description</Table.Th><Table.Th ta="right">Debit</Table.Th><Table.Th ta="right">Credit</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{lines.map((line, index) => <Table.Tr key={String(line.id ?? index)}><Table.Td><Text fw={700}>{String(line.account_name || 'Unknown account')}</Text><Text size="xs" c="dimmed">{String(line.account_code || '')}</Text></Table.Td><Table.Td>{String(line.description || '—')}</Table.Td><Table.Td ta="right">{money(line.debit)}</Table.Td><Table.Td ta="right">{money(line.credit)}</Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer></Card></Stack>;
}

export function JournalsPage() {
  return <RecordsPage eyebrow="ACCOUNTING" title="Journal entries" subtitle="Posted and draft accounting entries generated by ERP operations." list={api.accounting.journalEntries} details={{ load: api.accounting.journalEntry, render: (data) => <JournalDetails data={data} /> }} columns={[{ key: 'number', label: '#' }, { key: 'entry_date', label: 'Date' }, { key: 'description', label: 'Description' }, { key: 'reference', label: 'Reference' }, { key: 'status', label: 'Status', format: (value) => <Badge color={String(value) === 'posted' ? 'teal' : 'yellow'} variant="light">{String(value)}</Badge> }]} actions={[{ label: 'Post', color: 'teal', visible: (row) => String(row.status) === 'draft', run: (row) => api.accounting.postJournalEntry(Number(row.id)) }]} />;
}

export function StatementsPage() {
  const [from, setFrom] = useState<string | null>(new Date(new Date().getFullYear(), 0, 1).toISOString().slice(0, 10));
  const [to, setTo] = useState<string | null>(new Date().toISOString().slice(0, 10));
  const [data, setData] = useState<Record<string, Record<string, unknown>> | null>(null);
  const [loading, setLoading] = useState(false);
  async function load() {
    if (!from || !to) return;
    if (to < from) { notifications.show({ title: 'Invalid dates', message: 'The end date must be on or after the start date.', color: 'red' }); return; }
    setLoading(true);
    try {
      const params = query({ from, to });
      const [pnl, bs, cf] = await Promise.all([api.accounting.profitAndLoss(params), api.accounting.balanceSheet(query({ as_of: to })), api.accounting.cashFlow(params)]);
      setData({ pnl: pnl as Record<string, unknown>, bs: bs as Record<string, unknown>, cf: cf as Record<string, unknown> });
    } catch (error) { notifications.show({ title: 'Report failed', message: error instanceof Error ? error.message : 'Request failed', color: 'red' }); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  return <Stack gap="xl"><Group justify="space-between" align="flex-end" wrap="wrap"><div><Text size="sm" c="indigo.3" fw={800}>ACCOUNTING</Text><Title order={1} mt={4}>Financial statements</Title><Text c="dimmed" mt={4}>P&L, balance sheet and cash flow from posted journal activity.</Text></div><Button loading={loading} onClick={() => void load()} variant="light">Refresh statements</Button></Group><Group grow maw={700}><DatePickerInput label="From" value={from} onChange={setFrom} /><DatePickerInput label="To" value={to} onChange={setTo} /></Group>{data ? <SimpleGrid cols={{ base: 1, md: 3 }}><Card className="glass" withBorder radius="lg"><Text fw={800}>P&L</Text><Text size="sm" c="dimmed" mt="md">Revenue</Text><Text fw={800} size="xl">{money(data.pnl.total_revenue)}</Text><Text size="sm" c="dimmed" mt="md">Expenses</Text><Text fw={800} size="xl">{money(data.pnl.total_expenses)}</Text><Text size="sm" c="dimmed" mt="md">Net income</Text><Text fw={900} size="2xl">{money(data.pnl.net_income)}</Text></Card><Card className="glass" withBorder radius="lg"><Text fw={800}>Balance sheet</Text><Text size="sm" c="dimmed" mt="md">Assets</Text><Text fw={900} size="2xl">{money(data.bs.total_assets)}</Text><Text size="sm" c="dimmed" mt="md">Liabilities</Text><Text fw={800} size="xl">{money(data.bs.total_liabilities)}</Text><Badge mt="md" color={data.bs.balanced ? 'teal' : 'red'}>{data.bs.balanced ? 'Balanced' : 'Unbalanced'}</Badge></Card><Card className="glass" withBorder radius="lg"><Text fw={800}>Cash flow</Text><Text size="sm" c="dimmed" mt="md">Opening</Text><Text fw={800} size="xl">{money(data.cf.opening_cash)}</Text><Text size="sm" c="dimmed" mt="md">Net change</Text><Text fw={900} size="2xl">{money(data.cf.net_change)}</Text><Text size="sm" c="dimmed" mt="md">Ending</Text><Text fw={800} size="xl">{money(data.cf.ending_cash)}</Text></Card></SimpleGrid> : <Text c="dimmed">No statement data available for this range.</Text>}</Stack>;
}
