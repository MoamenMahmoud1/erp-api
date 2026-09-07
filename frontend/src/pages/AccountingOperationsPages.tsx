import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { DatePickerInput } from '@mantine/dates';
import { Badge, Button, Card, Group, Modal, Select, SimpleGrid, Stack, Text, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';

import { CrudPage } from '../components/CrudPage';
import { RecordsPage } from '../components/RecordsPage';
import { api, query, type Paginated } from '../lib/api';

export function ExpensesPage() {
  return (
    <CrudPage
      title="Expenses"
      subtitle="Record operating expenses against a payment account."
      list={api.accounting.expenses}
      create={api.accounting.createExpense}
      update={async () => undefined}
      canDelete={false}
      fields={[
        { key: 'expense_account', label: 'Expense account ID', type: 'number', required: true },
        { key: 'payment_account', label: 'Payment account ID', type: 'number', required: true },
        { key: 'amount', label: 'Amount', type: 'number', required: true },
        { key: 'expense_date', label: 'Date', required: true },
        { key: 'description', label: 'Description', required: true },
        { key: 'reference', label: 'Reference' },
      ]}
      columns={[{ key: 'id', label: '#' }, { key: 'expense_date', label: 'Date' }, { key: 'description', label: 'Description' }, { key: 'amount', label: 'Amount' }, { key: 'expense_account', label: 'Expense account' }, { key: 'payment_account', label: 'Payment account' }]}
    />
  );
}

export function PeriodsPage() {
  return <PeriodWorkspace />;
}

function PeriodWorkspace() {
  const [data, setData] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [modal, setModal] = useState(false);
  const [name, setName] = useState('');
  const [start, setStart] = useState<string | null>(null);
  const [end, setEnd] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try { setData(await api.accounting.periods('?page_size=50')); }
    catch (error) { notifications.show({ title: 'Unable to load periods', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  async function create() {
    if (!name || !start || !end) return;
    try {
      await api.accounting.createPeriod({ name, start_date: start, end_date: end });
      setModal(false); setName(''); setStart(null); setEnd(null); await load();
      notifications.show({ title: 'Period created', message: 'The accounting period is open.', color: 'teal' });
    } catch (error) { notifications.show({ title: 'Unable to create period', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
  }

  async function close(id: number) {
    if (!window.confirm('Close this accounting period? New journals will be blocked inside it.')) return;
    try { await api.accounting.closePeriod(id); await load(); notifications.show({ title: 'Period closed', message: 'The period is now locked.', color: 'teal' }); }
    catch (error) { notifications.show({ title: 'Unable to close period', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
  }

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="flex-end"><div><Text size="sm" c="indigo.3" fw={800}>ACCOUNTING</Text><Title order={1} mt={4}>Periods</Title><Text c="dimmed" mt={4}>Control which accounting dates are open for posting.</Text></div><Button onClick={() => setModal(true)} variant="gradient" gradient={{ from: 'indigo', to: 'cyan', deg: 120 }}>New period</Button></Group>
      <RecordsPage
        eyebrow="ACCOUNTING"
        title="Open and closed periods"
        subtitle="Period locking is enforced by the accounting posting service."
        list={async () => data}
        columns={[{ key: 'name', label: 'Period' }, { key: 'start_date', label: 'Start' }, { key: 'end_date', label: 'End' }, { key: 'is_closed', label: 'Closed' }, { key: 'closed_at', label: 'Closed at' }]}
        actions={[{ label: 'Close', color: 'red', run: (row) => api.accounting.closePeriod(Number(row.id)) }]}
      />
      <Modal opened={modal} onClose={() => setModal(false)} title="New accounting period" centered>
        <Stack><TextInput label="Name" value={name} onChange={(event) => setName(event.currentTarget.value)} required /><DatePickerInput label="Start date" value={start} onChange={setStart} required /><DatePickerInput label="End date" value={end} onChange={setEnd} required /><Button onClick={() => void create()}>Create period</Button></Stack>
      </Modal>
    </Stack>
  );
}

export function GeneralLedgerPage() {
  const [accounts, setAccounts] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [account, setAccount] = useState('');
  const [from, setFrom] = useState<string | null>(null);
  const [to, setTo] = useState<string | null>(null);
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { api.accounting.accounts('?page_size=100').then(setAccounts).catch(() => undefined); }, []);

  async function load() {
    if (!account) return;
    setLoading(true);
    try { setData(await api.accounting.generalLedger(query({ account: Number(account), from: from || undefined, to: to || undefined })) as Record<string, unknown>); }
    catch (error) { notifications.show({ title: 'Ledger failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
    finally { setLoading(false); }
  }

  const selected = data?.account as Record<string, unknown> | undefined;
  const lines = (data?.lines || []) as Record<string, unknown>[];

  return (
    <Stack gap="xl">
      <div><Text size="sm" c="indigo.3" fw={800}>ACCOUNTING</Text><Title order={1} mt={4}>General ledger</Title><Text c="dimmed" mt={4}>Inspect every posted debit, credit and running balance for an account.</Text></div>
      <Card className="glass" radius="lg" withBorder><SimpleGrid cols={{ base: 1, md: 4 }}><Select label="Account" searchable data={accounts.results.map((row) => ({ value: String(row.id), label: `${row.code || row.id} · ${row.name || ''}` }))} value={account} onChange={(value) => setAccount(value || '')} /><DatePickerInput label="From" value={from} onChange={setFrom} clearable /><DatePickerInput label="To" value={to} onChange={setTo} clearable /><Button mt={25} loading={loading} onClick={() => void load()}>Load ledger</Button></SimpleGrid></Card>
      {selected && <Card className="glass bento-card" radius="lg" withBorder><Group justify="space-between"><div><Text fw={800}>{String(selected.name)}</Text><Text size="sm" c="dimmed">{String(selected.code)}</Text></div><Badge variant="light">{String(selected.account_type)}</Badge></Group><SimpleGrid cols={{ base: 1, md: 3 }} mt="lg"><Text>Entries <b>{lines.length}</b></Text><Text>Last balance <b>{String(lines.at(-1)?.balance ?? '0.00')}</b></Text><Text>Normal side <b>{String(selected.normal_side || '—')}</b></Text></SimpleGrid></Card>}
      {!!lines.length && <RecordsPage eyebrow="LEDGER" title="Transactions" subtitle="Posted journal lines ordered chronologically." list={async () => ({ count: lines.length, next: null, previous: null, results: lines })} columns={[{ key: 'entry_number', label: '#' }, { key: 'entry_date', label: 'Date' }, { key: 'description', label: 'Description' }, { key: 'reference', label: 'Reference' }, { key: 'debit', label: 'Debit' }, { key: 'credit', label: 'Credit' }, { key: 'balance', label: 'Balance' }]} />}
    </Stack>
  );
}

export function TrialBalancePage() {
  const [from, setFrom] = useState<string | null>(null);
  const [to, setTo] = useState<string | null>(null);
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try { setData(await api.accounting.trialBalance(query({ from: from || undefined, to: to || undefined })) as Record<string, unknown>); }
    catch (error) { notifications.show({ title: 'Trial balance failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
    finally { setLoading(false); }
  }

  const rows = (data?.rows || []) as Record<string, unknown>[];
  return (
    <Stack gap="xl">
      <div><Text size="sm" c="indigo.3" fw={800}>ACCOUNTING</Text><Title order={1} mt={4}>Trial balance</Title><Text c="dimmed" mt={4}>A compact control report that verifies total debits equal total credits.</Text></div>
      <Card className="glass" withBorder radius="lg"><Group align="flex-end"><DatePickerInput label="From" value={from} onChange={setFrom} clearable /><DatePickerInput label="To" value={to} onChange={setTo} clearable /><Button loading={loading} onClick={() => void load()}>Run report</Button></Group></Card>
      {data && <SimpleGrid cols={{ base: 1, md: 3 }}><Card className="glass" withBorder><Text c="dimmed" size="xs">TOTAL DEBIT</Text><Text size="xl" fw={900}>{String(data.total_debit)}</Text></Card><Card className="glass" withBorder><Text c="dimmed" size="xs">TOTAL CREDIT</Text><Text size="xl" fw={900}>{String(data.total_credit)}</Text></Card><Card className="glass" withBorder><Badge color={data.balanced ? 'teal' : 'red'} size="lg">{data.balanced ? 'Balanced' : 'Unbalanced'}</Badge></Card></SimpleGrid>}
      {data && <RecordsPage eyebrow="CONTROL REPORT" title="Account totals" subtitle="Grouped posted journal activity by account." list={async () => ({ count: rows.length, next: null, previous: null, results: rows })} columns={[{ key: 'account__code', label: 'Code' }, { key: 'account__name', label: 'Account' }, { key: 'account__account_type', label: 'Type' }, { key: 'debit', label: 'Debit' }, { key: 'credit', label: 'Credit' }, { key: 'balance', label: 'Balance' }]} />}
    </Stack>
  );
}
