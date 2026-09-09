import type { FormEvent, ReactNode } from 'react';
import { useEffect, useState } from 'react';
import {
  ActionIcon,
  Badge,
  Button,
  Checkbox,
  Group,
  Loader,
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
import { IconEdit, IconSearch, IconTrash } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';

import type { Json, Paginated } from '../lib/api';

export type CrudOption = { value: string; label: string };
export type CrudField = {
  key: string;
  label: string;
  type?: 'text' | 'number' | 'boolean' | 'select';
  options?: CrudOption[];
  required?: boolean;
  createOnly?: boolean;
  clearable?: boolean;
};
export type CrudColumn = {
  key: string;
  label: string;
  render?: (value: unknown, row: Record<string, unknown>) => ReactNode;
};

type Props = {
  title: string;
  singularTitle?: string;
  subtitle: string;
  fields: CrudField[];
  columns: CrudColumn[];
  list: (query: string) => Promise<Paginated>;
  create?: (body: Json) => Promise<unknown>;
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

export function CrudPage({
  title,
  singularTitle,
  subtitle,
  fields,
  columns,
  list,
  create,
  update,
  remove,
  canEdit = true,
  canDelete = true,
  searchPlaceholder = 'Search',
}: Props) {
  const [data, setData] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Record<string, unknown> | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>({});
  const pageSize = 20;
  const itemTitle = singularTitle || title.replace(/s$/i, '');

  async function load(targetPage = page) {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(targetPage), page_size: String(pageSize) });
      if (search.trim()) params.set('search', search.trim());
      setData(await list(`?${params.toString()}`));
    } catch (error) {
      notifications.show({ title: `Unable to load ${title.toLowerCase()}`, message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(page); }, [page]);

  function openCreate() {
    if (!create) return;
    setEditing(null);
    const initial: Record<string, unknown> = {};
    fields.forEach((field) => { initial[field.key] = field.type === 'boolean' ? true : ''; });
    setForm(initial);
    setModalOpen(true);
  }

  function openEdit(row: Record<string, unknown>) {
    if (!canEdit || !update) return;
    setEditing(row);
    const next: Record<string, unknown> = {};
    fields.forEach((field) => {
      if (field.createOnly) return;
      next[field.key] = row[field.key] ?? (field.type === 'boolean' ? false : '');
    });
    setForm(next);
    setModalOpen(true);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      if (editing && update) await update(Number(editing.id), form as Json);
      else if (create) await create(form as Json);
      else return;
      setModalOpen(false);
      notifications.show({ title: editing ? 'Updated' : 'Created', message: `${itemTitle} saved successfully.`, color: 'teal' });
      await load(page);
    } catch (error) {
      notifications.show({ title: 'Save failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    }
  }

  async function onDelete(id: number) {
    if (!remove || !canDelete) return;
    if (!window.confirm(`Delete #${id}?`)) return;
    try {
      await remove(id);
      const nextPage = page > 1 && data.results.length === 1 ? page - 1 : page;
      if (nextPage !== page) setPage(nextPage);
      await load(nextPage);
      notifications.show({ title: 'Deleted', message: 'The record was removed.', color: 'teal' });
    } catch (error) {
      notifications.show({ title: 'Delete failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    }
  }

  const visibleFields = fields.filter((field) => !editing || !field.createOnly);
  const hasWrite = Boolean(create) || Boolean(canEdit && update) || Boolean(canDelete && remove);

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-end" wrap="wrap" gap="md">
        <div className="page-heading">
          <Text size="sm" c="erp.6" fw={700} tt="uppercase" lts="0.05em">{title === 'Products' ? 'Catalog' : 'Master data'}</Text>
          <Title order={1} mt={4}>{title}</Title>
          <Text c="dimmed" mt={4}>{subtitle}</Text>
        </div>
        {create && <Button onClick={openCreate} color="erp" radius="sm">Add {itemTitle}</Button>}
      </Group>

      <Paper className="records-toolbar" p="sm" radius="sm" withBorder>
        <Group gap="sm" wrap="wrap">
          <TextInput flex={1} radius="sm" leftSection={<IconSearch size={16} />} placeholder={searchPlaceholder} value={search} onChange={(event) => setSearch(event.currentTarget.value)} onKeyDown={(event) => { if (event.key === 'Enter') { setPage(1); void load(1); } }} />
          <Button radius="sm" variant="light" color="erp" onClick={() => { setPage(1); void load(1); }}>Search</Button>
        </Group>
      </Paper>

      <Paper className="surface-panel records-panel" radius="sm" withBorder>
        <ScrollArea>
          <Table horizontalSpacing="lg" verticalSpacing="sm" highlightOnHover striped={false} miw={720}>
            <Table.Thead><Table.Tr>{columns.map((column) => <Table.Th key={column.key}>{column.label}</Table.Th>)}{hasWrite && <Table.Th ta="right">Actions</Table.Th>}</Table.Tr></Table.Thead>
            <Table.Tbody>
              {data.results.map((row) => <Table.Tr key={String(row.id)}>{columns.map((column) => <Table.Td key={column.key}>{column.render ? column.render(row[column.key], row) : display(row[column.key])}</Table.Td>)}{hasWrite && <Table.Td><Group justify="flex-end" gap={4}>{canEdit && update && <ActionIcon radius="sm" variant="subtle" color="erp" aria-label={`Edit ${itemTitle}`} onClick={() => openEdit(row)}><IconEdit size={17} /></ActionIcon>}{canDelete && remove && <ActionIcon radius="sm" variant="subtle" color="red" aria-label={`Delete ${itemTitle}`} onClick={() => void onDelete(Number(row.id))}><IconTrash size={17} /></ActionIcon>}</Group></Table.Td>}</Table.Tr>)}
              {!loading && !data.results.length && <Table.Tr><Table.Td colSpan={columns.length + (hasWrite ? 1 : 0)}><div className="empty-state"><Text fw={700}>No records found</Text><Text size="sm" c="dimmed" mt={3}>{search ? 'Try a different search term.' : 'There is nothing to show here yet.'}</Text></div></Table.Td></Table.Tr>}
              {loading && <Table.Tr><Table.Td colSpan={columns.length + (hasWrite ? 1 : 0)}><Group justify="center" gap="xs" py="xl"><Loader size="sm" color="erp" /><Text c="dimmed" size="sm">Loading…</Text></Group></Table.Td></Table.Tr>}
            </Table.Tbody>
          </Table>
        </ScrollArea>
        <Group justify="space-between" p="md" className="records-footer" wrap="wrap"><Text size="sm" c="dimmed">{data.count.toLocaleString()} records</Text><Pagination total={Math.max(1, Math.ceil(data.count / pageSize))} value={page} onChange={setPage} color="erp" /></Group>
      </Paper>

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title={editing ? `Edit ${itemTitle}` : `Add ${itemTitle}`} centered size="md" radius="sm" overlayProps={{ backgroundOpacity: 0.20, blur: 0 }}>
        <form onSubmit={submit}><Stack gap="md">
          {visibleFields.map((field) => {
            if (field.type === 'boolean') return <Checkbox key={field.key} color="erp" label={field.label} checked={Boolean(form[field.key])} onChange={(event) => setForm((current) => ({ ...current, [field.key]: event.currentTarget.checked }))} />;
            if (field.type === 'number') return <NumberInput key={field.key} label={field.label} value={form[field.key] as number | string} onChange={(value) => setForm((current) => ({ ...current, [field.key]: value }))} required={field.required} radius="sm" />;
            if (field.type === 'select') return <Select key={field.key} label={field.label} data={field.options || []} value={String(form[field.key] ?? '')} onChange={(value) => setForm((current) => ({ ...current, [field.key]: value }))} required={field.required} allowDeselect={field.clearable === true} clearable={field.clearable === true} radius="sm" />;
            return <TextInput key={field.key} label={field.label} value={String(form[field.key] ?? '')} onChange={(event) => setForm((current) => ({ ...current, [field.key]: event.currentTarget.value }))} required={field.required} radius="sm" />;
          })}
          <Button type="submit" fullWidth radius="sm" color="erp" disabled={!create && !editing}>{editing ? 'Save changes' : `Add ${itemTitle}`}</Button>
        </Stack></form>
      </Modal>
    </Stack>
  );
}
