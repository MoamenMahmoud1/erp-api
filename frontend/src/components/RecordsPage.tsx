import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { Badge, Button, Group, Modal, Pagination, Paper, ScrollArea, Stack, Table, Text, Title, Loader } from '@mantine/core';
import { IconEye, IconRefresh } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';

import type { Paginated } from '../lib/api';

type Column = { key: string; label: string; format?: (value: unknown, row: Record<string, unknown>) => ReactNode };
type Action = { label: string; color?: string; visible?: (row: Record<string, unknown>) => boolean; run: (row: Record<string, unknown>) => Promise<unknown> };
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
};

function format(value: unknown) {
  if (value === true) return <Badge color="teal" variant="light">Yes</Badge>;
  if (value === false) return <Badge color="gray" variant="light">No</Badge>;
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function GenericDetails({ data }: { data: Record<string, unknown> }) {
  return (
    <Stack gap="sm">
      {Object.entries(data).filter(([key]) => !['items', 'allocations', 'lines'].includes(key)).map(([key, value]) => (
        <Group key={key} justify="space-between" align="flex-start" wrap="nowrap">
          <Text size="sm" c="dimmed">{key.replaceAll('_', ' ')}</Text>
          <Text size="sm" fw={600} ta="right" maw="65%">{format(value)}</Text>
        </Group>
      ))}
    </Stack>
  );
}

export function RecordsPage({ eyebrow, title, subtitle, columns, list, actions = [], details, topContent, reloadKey = 0, clientPaginated = false }: Props) {
  const [data, setData] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailData, setDetailData] = useState<Record<string, unknown> | null>(null);
  const pageSize = 20;

  async function load(targetPage = page) {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(targetPage), page_size: String(pageSize) });
      const result = await list(`?${params.toString()}`);
      const nextData = clientPaginated
        ? { ...result, results: result.results.slice((targetPage - 1) * pageSize, targetPage * pageSize) }
        : result;
      setData(nextData);
    } catch (error) {
      notifications.show({ title: 'Unable to load records', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(page); }, [page, reloadKey]);

  async function runAction(action: Action, row: Record<string, unknown>) {
    try { await action.run(row); notifications.show({ title: 'Done', message: `${action.label} completed.`, color: 'teal' }); await load(page); }
    catch (error) { notifications.show({ title: `${action.label} failed`, message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
  }

  async function openDetails(row: Record<string, unknown>) {
    if (!details) return;
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailData(null);
    try {
      const result = await details.load(Number(row.id));
      setDetailData(result as Record<string, unknown>);
    } catch (error) {
      setDetailOpen(false);
      notifications.show({ title: 'Unable to load details', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    } finally { setDetailLoading(false); }
  }

  const hasActionColumn = details || actions.length > 0;
  const visibleActions = data.results.some((row) => actions.some((action) => !action.visible || action.visible(row)));
  const showActionColumn = Boolean(hasActionColumn && (details || visibleActions));

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="flex-end" wrap="wrap">
        <div>
          <Text size="sm" c="indigo.3" fw={800}>{eyebrow}</Text>
          <Title order={1} mt={4}>{title}</Title>
          <Text c="dimmed" mt={4}>{subtitle}</Text>
        </div>
        {topContent ? <Group gap="xs" justify="flex-end">{topContent}</Group> : <div />}
        <Button variant="light" leftSection={<IconRefresh size={16} />} loading={loading} onClick={() => void load()}>Refresh</Button>
      </Group>
      <Paper className="glass bento-card" radius="lg" withBorder>
        <ScrollArea><Table miw={900} highlightOnHover>
          <Table.Thead><Table.Tr>{columns.map((column) => <Table.Th key={column.key}>{column.label}</Table.Th>)}{showActionColumn && <Table.Th ta="right">Actions</Table.Th>}</Table.Tr></Table.Thead>
          <Table.Tbody>
            {data.results.map((row) => {
              const rowActions = actions.filter((action) => !action.visible || action.visible(row));
              return <Table.Tr key={String(row.id ?? JSON.stringify(row))}>{columns.map((column) => <Table.Td key={column.key}>{column.format ? column.format(row[column.key], row) : format(row[column.key])}</Table.Td>)}{showActionColumn && <Table.Td><Group justify="flex-end" gap={6}>{details && <Button size="xs" variant="light" leftSection={<IconEye size={14} />} onClick={() => void openDetails(row)}>Details</Button>}{rowActions.map((action) => <Button key={action.label} size="xs" variant="light" color={action.color} onClick={() => void runAction(action, row)}>{action.label}</Button>)}</Group></Table.Td>}</Table.Tr>;
            })}
            {!loading && !data.results.length && <Table.Tr><Table.Td colSpan={columns.length + (showActionColumn ? 1 : 0)}><Text c="dimmed" ta="center" py="xl">No records found.</Text></Table.Td></Table.Tr>}
            {loading && <Table.Tr><Table.Td colSpan={columns.length + (showActionColumn ? 1 : 0)}><Text c="dimmed" ta="center" py="xl">Loading…</Text></Table.Td></Table.Tr>}
          </Table.Tbody>
        </Table></ScrollArea>
        <Group justify="space-between" p="md"><Text size="sm" c="dimmed">{data.count.toLocaleString()} records</Text><Pagination total={Math.max(1, Math.ceil(data.count / pageSize))} value={page} onChange={setPage} /></Group>
      </Paper>
      <Modal opened={detailOpen} onClose={() => setDetailOpen(false)} title={`${title} details`} centered size="lg" radius="xl">
        {detailLoading ? <Group justify="center" py="xl"><Loader size="sm" /></Group> : detailData ? (details?.render ? details.render(detailData) : <GenericDetails data={detailData} />) : <Text c="dimmed">No detail data available.</Text>}
      </Modal>
    </Stack>
  );
}
