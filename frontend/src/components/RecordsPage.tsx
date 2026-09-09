import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { Badge, Button, Group, Loader, Modal, Pagination, Paper, ScrollArea, Stack, Table, Text, TextInput, Title } from '@mantine/core';
import { IconEye, IconRefresh, IconSearch } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';

import type { Paginated } from '../lib/api';

type Column = { key: string; label: string; format?: (value: unknown, row: Record<string, unknown>) => ReactNode };
type Action = {
  label: string;
  color?: string;
  visible?: (row: Record<string, unknown>) => boolean;
  confirm?: string | ((row: Record<string, unknown>) => string);
  run: (row: Record<string, unknown>) => Promise<unknown>;
};
type Details = {
  load: (id: number) => Promise<unknown>;
  render?: (data: Record<string, unknown>) => ReactNode;
};

type Props = {
  eyebrow: string;
  title: string;
  subtitle: string;
  columns: Column[];
  list: (query: string) => Promise<Paginated>;
  actions?: Action[];
  details?: Details;
  topContent?: ReactNode;
  reloadKey?: number;
  clientPaginated?: boolean;
  searchPlaceholder?: string;
};

function format(value: unknown) {
  if (value === true) return <Badge color="teal" variant="light">Yes</Badge>;
  if (value === false) return <Badge color="gray" variant="light">No</Badge>;
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'number') return value.toLocaleString();
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function GenericDetails({ data }: { data: Record<string, unknown> }) {
  return (
    <Stack gap="sm">
      {Object.entries(data)
        .filter(([key]) => !['items', 'allocations', 'lines'].includes(key))
        .map(([key, value]) => (
          <Group key={key} justify="space-between" align="flex-start" wrap="nowrap" className="detail-row">
            <Text size="sm" c="dimmed">{key.replaceAll('_', ' ')}</Text>
            <Text size="sm" fw={600} ta="right" maw="65%" style={{ overflowWrap: 'anywhere' }}>{format(value)}</Text>
          </Group>
        ))}
    </Stack>
  );
}

export function RecordsPage({
  eyebrow,
  title,
  subtitle,
  columns,
  list,
  actions = [],
  details,
  topContent,
  reloadKey = 0,
  clientPaginated = false,
  searchPlaceholder = 'Search records…',
}: Props) {
  const [data, setData] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailData, setDetailData] = useState<Record<string, unknown> | null>(null);
  const pageSize = 20;

  async function load(targetPage = page, targetSearch = search) {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(targetPage), page_size: String(clientPaginated ? 500 : pageSize) });
      if (targetSearch.trim()) params.set('search', targetSearch.trim());
      const result = await list(`?${params.toString()}`);
      const nextData = clientPaginated
        ? { ...result, results: result.results.slice((targetPage - 1) * pageSize, targetPage * pageSize), count: result.results.length }
        : result;
      setData(nextData);
    } catch (error) {
      notifications.show({ title: `Unable to load ${title.toLowerCase()}`, message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(page); }, [page, reloadKey]);

  async function searchRecords() {
    setPage(1);
    await load(1, search);
  }

  async function runAction(action: Action, row: Record<string, unknown>) {
    if (action.confirm) {
      const message = typeof action.confirm === 'function' ? action.confirm(row) : action.confirm;
      if (!window.confirm(message)) return;
    }
    try {
      await action.run(row);
      notifications.show({ title: 'Done', message: `${action.label} completed.`, color: 'teal' });
      await load(page);
    } catch (error) {
      notifications.show({ title: `${action.label} failed`, message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    }
  }

  async function openDetails(row: Record<string, unknown>) {
    if (!details) return;
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailData(null);
    try {
      const id = Number(row.id);
      if (!Number.isInteger(id) || id <= 0) throw new Error('This record does not have a valid identifier.');
      const result = await details.load(id);
      setDetailData(result as Record<string, unknown>);
    } catch (error) {
      setDetailOpen(false);
      notifications.show({ title: 'Unable to load details', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    } finally {
      setDetailLoading(false);
    }
  }

  const visibleActions = data.results.some((row) => actions.some((action) => !action.visible || action.visible(row)));
  const showActionColumn = Boolean(details || visibleActions);
  const totalPages = Math.max(1, Math.ceil(data.count / pageSize));

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-end" wrap="wrap" gap="md">
        <div className="page-heading">
          <Text size="sm" c="blue.5" fw={700} tt="uppercase" lts="0.05em">{eyebrow}</Text>
          <Title order={1} mt={4}>{title}</Title>
          <Text c="dimmed" mt={4} maw={760}>{subtitle}</Text>
        </div>
        <Group gap="xs" wrap="wrap" justify="flex-end">
          {topContent}
          <Button variant="light" leftSection={<IconRefresh size={16} />} loading={loading} onClick={() => void load()} radius="md">Refresh</Button>
        </Group>
      </Group>

      <Paper className="records-toolbar" p="sm" radius="md" withBorder>
        <Group gap="sm" wrap="wrap">
          <TextInput
            className="records-search"
            flex={1}
            miw={240}
            leftSection={<IconSearch size={16} />}
            placeholder={searchPlaceholder}
            value={search}
            onChange={(event) => setSearch(event.currentTarget.value)}
            onKeyDown={(event) => { if (event.key === 'Enter') void searchRecords(); if (event.key === 'Escape') { setSearch(''); void load(1, ''); setPage(1); } }}
            radius="md"
            aria-label={`Search ${title}`}
          />
          <Button radius="md" onClick={() => void searchRecords()}>Search</Button>
          {search && <Button radius="md" variant="subtle" onClick={() => { setSearch(''); setPage(1); void load(1, ''); }}>Clear</Button>}
        </Group>
      </Paper>

      <Paper className="surface-panel records-panel" radius="md" withBorder>
        <ScrollArea type="auto" offsetScrollbars>
          <Table miw={820} highlightOnHover verticalSpacing="sm" horizontalSpacing="md">
            <Table.Thead className="records-thead">
              <Table.Tr>
                {columns.map((column) => <Table.Th key={column.key}>{column.label}</Table.Th>)}
                {showActionColumn && <Table.Th ta="right">Actions</Table.Th>}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data.results.map((row) => {
                const rowActions = actions.filter((action) => !action.visible || action.visible(row));
                return (
                  <Table.Tr key={String(row.id ?? JSON.stringify(row))}>
                    {columns.map((column) => <Table.Td key={column.key}>{column.format ? column.format(row[column.key], row) : format(row[column.key])}</Table.Td>)}
                    {showActionColumn && (
                      <Table.Td>
                        <Group justify="flex-end" gap={6} wrap="wrap">
                          {details && <Button size="xs" variant="light" leftSection={<IconEye size={14} />} onClick={() => void openDetails(row)} radius="sm">Details</Button>}
                          {rowActions.map((action) => <Button key={action.label} size="xs" variant="light" color={action.color} onClick={() => void runAction(action, row)} radius="sm">{action.label}</Button>)}
                        </Group>
                      </Table.Td>
                    )}
                  </Table.Tr>
                );
              })}
              {!loading && !data.results.length && (
                <Table.Tr>
                  <Table.Td colSpan={columns.length + (showActionColumn ? 1 : 0)}>
                    <div className="empty-state"><Text fw={700}>No records found</Text><Text size="sm" c="dimmed" mt={3}>{search ? 'Try a different search term.' : 'There is nothing to show here yet.'}</Text></div>
                  </Table.Td>
                </Table.Tr>
              )}
              {loading && (
                <Table.Tr>
                  <Table.Td colSpan={columns.length + (showActionColumn ? 1 : 0)}><Group justify="center" gap="xs" py="xl"><Loader size="sm" /><Text c="dimmed" size="sm">Loading…</Text></Group></Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </ScrollArea>
        <Group justify="space-between" align="center" p="md" wrap="wrap" className="records-footer">
          <Text size="sm" c="dimmed">{data.count.toLocaleString()} records</Text>
          <Pagination total={totalPages} value={Math.min(page, totalPages)} onChange={setPage} boundaries={1} siblings={1} />
        </Group>
      </Paper>

      <Modal opened={detailOpen} onClose={() => setDetailOpen(false)} title={`${title} details`} centered size="lg" radius="md" fullScreen={false}>
        {detailLoading ? <Group justify="center" py="xl"><Loader size="sm" /></Group> : detailData ? (details?.render ? details.render(detailData) : <GenericDetails data={detailData} />) : <Text c="dimmed">No detail data available.</Text>}
      </Modal>
    </Stack>
  );
}
