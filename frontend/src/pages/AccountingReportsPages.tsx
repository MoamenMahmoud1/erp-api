import type { FormEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { DatePickerInput } from '@mantine/dates';
import { Badge, Button, Card, Group, NumberInput, Select, SimpleGrid, Stack, Table, Text, TextInput, Title } from '@mantine/core';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';

import { api, type Paginated } from '../lib/api';

const today = () => new Date().toISOString().slice(0, 10);
const money = (value: unknown) => Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

type AgingReport = { customers?: Record<string, unknown>[]; suppliers?: Record<string, unknown>[] };
type BalanceReport = { customers?: Record<string, unknown>[]; suppliers?: Record<string, unknown>[] };
type LineDraft = { account: string; description: string; debit: number | string; credit: number | string };

export function BalancesPage() {
  const [asOf, setAsOf] = useState<string | null>(today());
  const [customerRows, setCustomerRows] = useState<Record<string, unknown>[]>([]);
  const [supplierRows, setSupplierRows] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    if (!asOf) return;
    setLoading(true);
    try {
      const [customers, suppliers] = await Promise.all([
        api.accounting.customerBalances(`?as_of=${asOf}`) as Promise<BalanceReport>,
        api.accounting.supplierBalances(`?as_of=${asOf}`) as Promise<BalanceReport>,
      ]);
      setCustomerRows(customers.customers || []);
      setSupplierRows(suppliers.suppliers || []);
    } catch (error) {
      notifications.show({ title: 'Balance report failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    } finally { setLoading(false); }
  };

  useEffect(() => { void load(); }, []);

  const table = (rows: Record<string, unknown>[], nameKey: string, totalKey: string) => (
    <Table highlightOnHover>
      <Table.Thead><Table.Tr><Table.Th>Party</Table.Th><Table.Th>{totalKey === 'invoiced' ? 'Invoiced' : 'Purchased'}</Table.Th><Table.Th>Paid</Table.Th><Table.Th>Returns</Table.Th><Table.Th>Balance</Table.Th></Table.Tr></Table.Thead>
      <Table.Tbody>{rows.map((row) => <Table.Tr key={String(row.customer_id || row.supplier_id)}><Table.Td>{String(row[nameKey] || '')}</Table.Td><Table.Td>{money(row[totalKey])}</Table.Td><Table.Td>{money(row.paid)}</Table.Td><Table.Td>{money(row.returns)}</Table.Td><Table.Td fw={800}>{money(row.balance)}</Table.Td></Table.Tr>)}</Table.Tbody>
    </Table>
  );

  return <Stack gap="xl"><div><Text size="sm" c="indigo.3" fw={800}>ACCOUNTING</Text><Title order={1} mt={4}>AR / AP</Title><Text c="dimmed" mt={4}>Customer receivables and supplier payables as of a selected date.</Text></div><Group justify="flex-end"><DatePickerInput value={asOf} onChange={setAsOf} /><Button loading={loading} onClick={() => void load()}>Refresh</Button></Group><SimpleGrid cols={{ base: 1, lg: 2 }}><Card className="glass" withBorder radius="lg"><Text fw={800} mb="md">Customer balances</Text>{table(customerRows, 'customer_name', 'invoiced')}</Card><Card className="glass" withBorder radius="lg"><Text fw={800} mb="md">Supplier balances</Text>{table(supplierRows, 'supplier_name', 'purchased')}</Card></SimpleGrid><Group justify="space-between" align="flex-end"><div><Text fw={800}>Aging</Text><Text size="xs" c="dimmed">Outstanding balances grouped by invoice or purchase age.</Text></div></Group><AgingSection asOf={asOf} loading={loading} onRefresh={load} /></Stack>;
}

function AgingSection({ asOf, loading, onRefresh }: { asOf: string | null; loading: boolean; onRefresh: () => Promise<void> }) {
  const [customers, setCustomers] = useState<Record<string, unknown>[]>([]);
  const [suppliers, setSuppliers] = useState<Record<string, unknown>[]>([]);
  const [loaded, setLoaded] = useState(false);

  const load = async () => {
    if (!asOf) return;
    try {
      const [customer, supplier] = await Promise.all([api.accounting.customerAging(`?as_of=${asOf}`) as Promise<AgingReport>, api.accounting.supplierAging(`?as_of=${asOf}`) as Promise<AgingReport>]);
      setCustomers(customer.customers || []); setSuppliers(supplier.suppliers || []); setLoaded(true);
    } catch (error) { notifications.show({ title: 'Aging failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
  };

  useEffect(() => { void load(); }, [asOf]);
  const table = (rows: Record<string, unknown>[], nameKey: string, idKey: string) => <Table highlightOnHover><Table.Thead><Table.Tr><Table.Th>Party</Table.Th><Table.Th>0–30</Table.Th><Table.Th>31–60</Table.Th><Table.Th>61–90</Table.Th><Table.Th>90+</Table.Th><Table.Th>Total</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{rows.map((row) => <Table.Tr key={String(row[idKey])}><Table.Td>{String(row[nameKey] || '')}</Table.Td><Table.Td>{money(row['0_30'])}</Table.Td><Table.Td>{money(row['31_60'])}</Table.Td><Table.Td>{money(row['61_90'])}</Table.Td><Table.Td>{money(row['90_plus'])}</Table.Td><Table.Td fw={800}>{money(row.total)}</Table.Td></Table.Tr>)}</Table.Tbody></Table>;
  return <SimpleGrid cols={{ base: 1, lg: 2 }}>{<Card className="glass" withBorder radius="lg"><Group justify="space-between" mb="md"><Text fw={800}>Customer aging</Text><Button size="xs" variant="subtle" loading={loading} onClick={() => void onRefresh()}>Balances</Button></Group>{loaded ? table(customers, 'customer_name', 'customer_id') : <Text c="dimmed">Loading…</Text>}</Card>}<Card className="glass" withBorder radius="lg"><Text fw={800} mb="md">Supplier aging</Text>{loaded ? table(suppliers, 'supplier_name', 'supplier_id') : <Text c="dimmed">Loading…</Text>}</Card></SimpleGrid>;
}

export function OpeningBalancePage() {
  const [accounts, setAccounts] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [entryDate, setEntryDate] = useState<string | null>(today());
  const [lines, setLines] = useState<LineDraft[]>([{ account: '', description: '', debit: 0, credit: 0 }, { account: '', description: '', debit: 0, credit: 0 }]);
  const [loading, setLoading] = useState(false);

  useEffect(() => { api.accounting.accounts('?page_size=50').then(setAccounts).catch(() => undefined); }, []);
  const options = useMemo(() => accounts.results.map((row) => ({ value: String(row.id), label: `${row.code || row.id} · ${row.name || ''}` })), [accounts]);
  const setLine = (index: number, patch: Partial<LineDraft>) => setLines((current) => current.map((line, i) => i === index ? { ...line, ...patch } : line));
  const debit = lines.reduce((sum, line) => sum + Number(line.debit || 0), 0);
  const credit = lines.reduce((sum, line) => sum + Number(line.credit || 0), 0);

  async function submit() {
    if (!entryDate || debit <= 0 || Math.abs(debit - credit) > 0.0001 || lines.some((line) => !line.account || (Number(line.debit) > 0 && Number(line.credit) > 0))) return;
    setLoading(true);
    try { await api.accounting.openingBalance({ entry_date: entryDate, lines: lines.map((line) => ({ account: Number(line.account), description: line.description, debit: Number(line.debit || 0), credit: Number(line.credit || 0) })) }); notifications.show({ title: 'Opening balance posted', message: 'The initial journal entry was created.', color: 'teal' }); setLines([{ account: '', description: '', debit: 0, credit: 0 }, { account: '', description: '', debit: 0, credit: 0 }]); }
    catch (error) { notifications.show({ title: 'Opening balance failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
    finally { setLoading(false); }
  }

  return <Stack gap="xl"><div><Text size="sm" c="indigo.3" fw={800}>ACCOUNTING</Text><Title order={1} mt={4}>Opening balance</Title><Text c="dimmed" mt={4}>Enter the company's starting balances as one posted journal.</Text></div><Card className="glass" withBorder radius="lg" p="xl"><Stack><DatePickerInput label="Entry date" value={entryDate} onChange={setEntryDate} required />{lines.map((line, index) => <SimpleGrid key={index} cols={{ base: 1, lg: 5 }}><Select label={`Account ${index + 1}`} searchable data={options} value={line.account} onChange={(value) => setLine(index, { account: value || '' })} required /><TextInput label="Description" value={line.description} onChange={(event) => setLine(index, { description: event.currentTarget.value })} /><NumberInput label="Debit" min={0} value={line.debit} onChange={(value) => setLine(index, { debit: value })} /><NumberInput label="Credit" min={0} value={line.credit} onChange={(value) => setLine(index, { credit: value })} /><Button color="red" variant="subtle" disabled={lines.length <= 2} onClick={() => setLines((current) => current.filter((_, i) => i !== index))}><IconTrash size={16} /> Remove</Button></SimpleGrid>)}<Button variant="light" leftSection={<IconPlus size={16} />} onClick={() => setLines((current) => [...current, { account: '', description: '', debit: 0, credit: 0 }])}>Add line</Button><Group justify="space-between"><Text fw={800}>Debit: {money(debit)} · Credit: {money(credit)}</Text><Button loading={loading} disabled={debit <= 0 || Math.abs(debit - credit) > 0.0001} onClick={() => void submit()} variant="gradient" gradient={{ from: 'indigo', to: 'cyan', deg: 120 }}>Post opening balance</Button></Group></Stack></Card></Stack>;
}

export function ManualJournalPage() {
  const [accounts, setAccounts] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [entryDate, setEntryDate] = useState<string | null>(today());
  const [description, setDescription] = useState('');
  const [reference, setReference] = useState('');
  const [lines, setLines] = useState<LineDraft[]>([{ account: '', description: '', debit: 0, credit: 0 }, { account: '', description: '', debit: 0, credit: 0 }]);
  const [loading, setLoading] = useState(false);
  useEffect(() => { api.accounting.accounts('?page_size=50').then(setAccounts).catch(() => undefined); }, []);
  const options = useMemo(() => accounts.results.map((row) => ({ value: String(row.id), label: `${row.code || row.id} · ${row.name || ''}` })), [accounts]);
  const setLine = (index: number, patch: Partial<LineDraft>) => setLines((current) => current.map((line, i) => i === index ? { ...line, ...patch } : line));
  const debit = lines.reduce((sum, line) => sum + Number(line.debit || 0), 0);
  const credit = lines.reduce((sum, line) => sum + Number(line.credit || 0), 0);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!entryDate || !description || debit <= 0 || Math.abs(debit - credit) > 0.0001 || lines.some((line) => !line.account || (Number(line.debit) > 0 && Number(line.credit) > 0))) return;
    setLoading(true);
    try { await api.accounting.createJournalEntry({ entry_date: entryDate, description, reference, lines: lines.map((line) => ({ account: Number(line.account), description: line.description, debit: Number(line.debit || 0), credit: Number(line.credit || 0) })) }); notifications.show({ title: 'Journal created', message: 'The balanced journal was saved as a draft.', color: 'teal' }); setDescription(''); setReference(''); setLines([{ account: '', description: '', debit: 0, credit: 0 }, { account: '', description: '', debit: 0, credit: 0 }]); }
    catch (error) { notifications.show({ title: 'Journal failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
    finally { setLoading(false); }
  }

  return <Stack gap="xl"><div><Text size="sm" c="indigo.3" fw={800}>ACCOUNTING</Text><Title order={1} mt={4}>Manual journal</Title><Text c="dimmed" mt={4}>Create a balanced draft for a correction or accounting adjustment.</Text></div><Card className="glass" withBorder radius="lg" p="xl"><form onSubmit={submit}><Stack><SimpleGrid cols={{ base: 1, md: 3 }}><DatePickerInput label="Entry date" value={entryDate} onChange={setEntryDate} required /><TextInput label="Description" value={description} onChange={(event) => setDescription(event.currentTarget.value)} required /><TextInput label="Reference" value={reference} onChange={(event) => setReference(event.currentTarget.value)} /></SimpleGrid>{lines.map((line, index) => <SimpleGrid key={index} cols={{ base: 1, lg: 5 }}><Select label={`Account ${index + 1}`} searchable data={options} value={line.account} onChange={(value) => setLine(index, { account: value || '' })} required /><TextInput label="Line description" value={line.description} onChange={(event) => setLine(index, { description: event.currentTarget.value })} /><NumberInput label="Debit" min={0} value={line.debit} onChange={(value) => setLine(index, { debit: value })} /><NumberInput label="Credit" min={0} value={line.credit} onChange={(value) => setLine(index, { credit: value })} /><Button type="button" color="red" variant="subtle" disabled={lines.length <= 2} onClick={() => setLines((current) => current.filter((_, i) => i !== index))}><IconTrash size={16} /> Remove</Button></SimpleGrid>)}<Button type="button" variant="light" leftSection={<IconPlus size={16} />} onClick={() => setLines((current) => [...current, { account: '', description: '', debit: 0, credit: 0 }])}>Add line</Button><Group justify="space-between"><Text fw={800}>Debit: {money(debit)} · Credit: {money(credit)}</Text><Button type="submit" loading={loading} disabled={debit <= 0 || Math.abs(debit - credit) > 0.0001} variant="gradient" gradient={{ from: 'indigo', to: 'cyan', deg: 120 }}>Create draft</Button></Group></Stack></form></Card></Stack>;
}
