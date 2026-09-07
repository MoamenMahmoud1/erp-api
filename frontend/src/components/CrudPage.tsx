import type { FormEvent, ReactNode } from 'react';
import { useEffect, useState } from 'react';
import {
  ActionIcon,
  Badge,
  Button,
  Checkbox,
  Group,
  Modal,
  NumberInput,
  Pagination,
  Paper,
  ScrollArea,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconEdit, IconPlus, IconSearch, IconTrash } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';

import type { Json, Paginated } from '../lib/api';

export type CrudOption = { value: string; label: string };
export type CrudField = { key: string; label: string; type?: 'text' | 'number' | 'boolean' | 'select'; options?: CrudOption[]; required?: boolean };
export type CrudColumn = { key: string; label: string; render?: (value: unknown, row: Record<string, unknown>) => ReactNode };

type Props = {
  title: string;
  subtitle: string;
  fields: CrudField[];
  columns: CrudColumn[];
  list: (query: string) => Promise<Paginated>;
  create: (body: Json) => Promise<unknown>;
  update?: (id: number, body: Json) => Promise<unknown>;
  remove?: (id: number) => Promise<unknown>;
  canEdit?: boolean;
  canDelete?: boolean;
  searchPlaceholder?: string;
};

function display(value: unknown) {
  if (value === true) return <Badge color="teal" variant="light">Active</Badge>;
  if (value === false) return <Badge color="gray" variant="light">No</Badge>;
  if (value === null || value === undefined || value === '') return '—';
  return String(value);
}

export function CrudPage({ title, subtitle, fields, columns, list, create, update, remove, canEdit = true, canDelete = true, searchPlaceholder = 'Search' }: Props) {
  const [data, setData] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Record<string, unknown> | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>({});
  const pageSize = 20;

  async function load(targetPage = page) {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(targetPage), page_size: String(pageSize) });
      if (search.trim()) params.set('search', search.trim());
      setData(await list(`?${params.toString()}`));
    } catch (error) {
      notifications.show({ title: `Unable to load ${title.toLowerCase()}`, message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(page); }, [page]);

  function openCreate() {
    setEditing(null);
    const initial: Record<string, unknown> = {};
    fields.forEach((field) => { if (field.type === 'boolean') initial[field.key] = true; else if (field.type === 'select') initial[field.key] = field.options?.[0]?.value ?? ''; else initial[field.key] = ''; });
    setForm(initial);
    setModalOpen(true);
  }

  function openEdit(row: Record<string, unknown>) {
    if (!canEdit || !update) return;
    setEditing(row);
    const next: Record<string, unknown> = {};
    fields.forEach((field) => { next[field.key] = row[field.key] ?? (field.type === 'boolean' ? false : ''); });
    setForm(next);
    setModalOpen(true);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      if (editing && update) await update(Number(editing.id), form as Json);
      else await create(form as Json);
      setModalOpen(false);
      notifications.show({ title: editing ? 'Updated' : 'Created', message: `${title.slice(0, -1)} saved successfully.`, color: 'teal' });
      await load(page);
    } catch (error) { notifications.show({ title: 'Save failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
  }

  async function onDelete(id: number) {
    if (!remove || !canDelete) return;
    if (!window.confirm(`Delete #${id}?`)) return;
    try { await remove(id); notifications.show({ title: 'Deleted', message: 'The record was removed.', color: 'teal' }); await load(page); }
    catch (error) { notifications.show({ title: 'Delete failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
  }

  const hasWrite = Boolean(canEdit && update) || Boolean(canDelete && remove) || Boolean(create);

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="flex-end" wrap="wrap"><div><Text size="sm" c="indigo.3" fw={800}>MASTER DATA</Text><Title order={1} mt={4}>{title}</Title><Text c="dimmed" mt={4}>{subtitle}</Text></div>{create && <Button leftSection={<IconPlus size={17} />} onClick={openCreate} variant="gradient" gradient={{ from: 'indigo', to: 'cyan', deg: 120 }}>New</Button>}</Group>
      <Paper className="glass" p="md" radius="lg" withBorder><Group><TextInput flex={1} leftSection={<IconSearch size={16} />} placeholder={searchPlaceholder} value={search} onChange={(event) => setSearch(event.currentTarget.value)} onKeyDown={(event) => { if (event.key === 'Enter') { setPage(1); void load(1); } }} /><Button variant="light" onClick={() => { setPage(1); void load(1); }}>Search</Button></Group></Paper>
      <Paper className="glass bento-card" radius="lg" withBorder>
        <ScrollArea><Table horizontalSpacing="lg" verticalSpacing="sm" highlightOnHover striped={false} miw={720}><Table.Thead><Table.Tr>{columns.map((column) => <Table.Th key={column.key}>{column.label}</Table.Th>)}{hasWrite && <Table.Th ta="right">Actions</Table.Th>}</Table.Tr></Table.Thead><Table.Tbody>
          {data.results.map((row) => <Table.Tr key={String(row.id)}>{columns.map((column) => <Table.Td key={column.key}>{column.render ? column.render(row[column.key], row) : display(row[column.key])}</Table.Td>)}{hasWrite && <Table.Td><Group justify="flex-end" gap={5}>{canEdit && update && <ActionIcon variant="subtle" onClick={() => openEdit(row)}><IconEdit size={17} /></ActionIcon>}{canDelete && remove && <ActionIcon variant="subtle" color="red" onClick={() => void onDelete(Number(row.id))}><IconTrash size={17} /></ActionIcon>}</Group></Table.Td>}</Table.Tr>)}
          {!loading && !data.results.length && <Table.Tr><Table.Td colSpan={columns.length + (hasWrite ? 1 : 0)}><Text c="dimmed" ta="center" py="xl">No records found.</Text></Table.Td></Table.Tr>}
          {loading && <Table.Tr><Table.Td colSpan={columns.length + (hasWrite ? 1 : 0)}><Text c="dimmed" ta="center" py="xl">Loading…</Text></Table.Td></Table.Tr>}
        </Table.Tbody></Table></ScrollArea>
        <Group justify="space-between" p="md"><Text size="sm" c="dimmed">{data.count.toLocaleString()} records</Text><Pagination total={Math.max(1, Math.ceil(data.count / pageSize))} value={page} onChange={setPage} /></Group>
      </Paper>
      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title={editing ? `Edit ${title.slice(0, -1)}` : `New ${title.slice(0, -1)}`} centered size="md"><form onSubmit={submit}><Stack>{fields.map((field) => { if (field.type === 'boolean') return <Checkbox key={field.key} label={field.label} checked={Boolean(form[field.key])} onChange={(event) => setForm((current) => ({ ...current, [field.key]: event.currentTarget.checked }))} />; if (field.type === 'number') return <NumberInput key={field.key} label={field.label} value={form[field.key] as number | string} onChange={(value) => setForm((current) => ({ ...current, [field.key]: value }))} required={field.required} />; if (field.type === 'select') return <Select key={field.key} label={field.label} data={field.options || []} value={String(form[field.key] ?? '')} onChange={(value) => setForm((current) => ({ ...current, [field.key]: value }))} required={field.required} allowDeselect={false} />; return <TextInput key={field.key} label={field.label} value={String(form[field.key] ?? '')} onChange={(event) => setForm((current) => ({ ...current, [field.key]: event.currentTarget.value }))} required={field.required} />; })}<Button type="submit" fullWidth>Save changes</Button></Stack></form></Modal>
    </Stack>
  );
}
