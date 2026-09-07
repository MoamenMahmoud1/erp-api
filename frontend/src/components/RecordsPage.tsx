import { useEffect, useState } from 'react';
import { Badge, Button, Group, Pagination, Paper, ScrollArea, Stack, Table, Text, Title } from '@mantine/core';
import { IconRefresh } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';

import type { Paginated } from '../lib/api';

type Column = { key: string; label: string; format?: (value: unknown, row: Record<string, unknown>) => React.ReactNode };
type Action = { label: string; color?: string; run: (row: Record<string, unknown>) => Promise<unknown> };

type Props = {
  eyebrow: string;
  title: string;
  subtitle: string;
  columns: Column[];
  list: (query: string) => Promise<Paginated>;
  actions?: Action[];
};

function format(value: unknown) {
  if (value === true) return <Badge color="teal" variant="light">Yes</Badge>;
  if (value === false) return <Badge color="gray" variant="light">No</Badge>;
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function RecordsPage({ eyebrow, title, subtitle, columns, list, actions = [] }: Props) {
  const [data, setData] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const pageSize = 20;

  async function load() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      setData(await list(`?${params.toString()}`));
    } catch (error) {
      notifications.show({ title: 'Unable to load records', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [page]);

  async function runAction(action: Action, row: Record<string, unknown>) {
    try {
      await action.run(row);
      notifications.show({ title: 'Done', message: `${action.label} completed.`, color: 'teal' });
      await load();
    } catch (error) {
      notifications.show({ title: `${action.label} failed`, message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    }
  }

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="flex-end">
        <div><Text size="sm" c="indigo.3" fw={800}>{eyebrow}</Text><Title order={1} mt={4}>{title}</Title><Text c="dimmed" mt={4}>{subtitle}</Text></div>
        <Button variant="light" leftSection={<IconRefresh size={16} />} loading={loading} onClick={() => void load()}>Refresh</Button>
      </Group>
      <Paper className="glass bento-card" radius="lg" withBorder>
        <ScrollArea>
          <Table miw={900} highlightOnHover>
            <Table.Thead><Table.Tr>{columns.map((column) => <Table.Th key={column.key}>{column.label}</Table.Th>)}{actions.length > 0 && <Table.Th ta="right">Actions</Table.Th>}</Table.Tr></Table.Thead>
            <Table.Tbody>
              {data.results.map((row) => (
                <Table.Tr key={String(row.id ?? JSON.stringify(row))}>
                  {columns.map((column) => <Table.Td key={column.key}>{column.format ? column.format(row[column.key], row) : format(row[column.key])}</Table.Td>)}
                  {actions.length > 0 && <Table.Td><Group justify="flex-end" gap={6}>{actions.map((action) => <Button key={action.label} size="xs" variant="light" color={action.color} onClick={() => void runAction(action, row)}>{action.label}</Button>)}</Group></Table.Td>}
                </Table.Tr>
              ))}
              {!loading && !data.results.length && <Table.Tr><Table.Td colSpan={columns.length + (actions.length ? 1 : 0)}><Text c="dimmed" ta="center" py="xl">No records found.</Text></Table.Td></Table.Tr>}
              {loading && <Table.Tr><Table.Td colSpan={columns.length + (actions.length ? 1 : 0)}><Text c="dimmed" ta="center" py="xl">Loading…</Text></Table.Td></Table.Tr>}
            </Table.Tbody>
          </Table>
        </ScrollArea>
        <Group justify="space-between" p="md"><Text size="sm" c="dimmed">{data.count.toLocaleString()} records</Text><Pagination total={Math.max(1, Math.ceil(data.count / pageSize))} value={page} onChange={setPage} /></Group>
      </Paper>
    </Stack>
  );
}
