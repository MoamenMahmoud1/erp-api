import { useEffect, useState } from 'react';
import { Badge, Button, Card, Group, Loader, NumberInput, Select, SimpleGrid, Stack, Text, Textarea, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';

import { api, type EmployeeShift, type Paginated, type UserProfile } from '../lib/api';

type Props = { user: UserProfile };

function formatMoney(value: number | string | null | undefined) {
  return Number(value || 0).toFixed(2);
}

export function ShiftPage({ user }: Props) {
  const [shift, setShift] = useState<EmployeeShift | null>(null);
  const [vehicles, setVehicles] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [openingCash, setOpeningCash] = useState<number | string>(0);
  const [vehicle, setVehicle] = useState<string>('');
  const [closingCash, setClosingCash] = useState<number | string>(0);
  const [closingTransfer, setClosingTransfer] = useState<number | string>(0);
  const [closingNotes, setClosingNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      const [currentShift, locationData] = await Promise.all([
        api.employees.currentShift(),
        api.inventory.locations('?page_size=100'),
      ]);
      setShift(currentShift);
      setVehicles({
        ...locationData,
        results: locationData.results.filter((row) => String(row.location_type) === 'SALES_VEHICLE'),
      });
    } catch (error) {
      notifications.show({ title: 'Shift unavailable', message: error instanceof Error ? error.message : 'Unable to load shift data.', color: 'red' });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function start() {
    setSaving(true);
    try {
      const created = await api.employees.startShift({ opening_cash: Number(openingCash || 0), vehicle: vehicle ? Number(vehicle) : null });
      setShift(created);
      notifications.show({ title: 'Shift started', message: `Shift opened for ${created.site_name}.`, color: 'teal' });
      window.dispatchEvent(new Event('erp-context-changed'));
    } catch (error) {
      notifications.show({ title: 'Unable to start shift', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    } finally {
      setSaving(false);
    }
  }

  async function close() {
    setSaving(true);
    try {
      const closed = await api.employees.closeShift({
        closing_cash: Number(closingCash || 0),
        closing_transfer: Number(closingTransfer || 0),
        closing_notes: closingNotes,
      });
      setShift(closed);
      notifications.show({
        title: 'Shift closed',
        message: `Cash difference: ${formatMoney(closed.cash_difference)} · Transfer difference: ${formatMoney(closed.transfer_difference)}`,
        color: Number(closed.cash_difference) === 0 && Number(closed.transfer_difference) === 0 ? 'teal' : 'orange',
      });
      window.dispatchEvent(new Event('erp-context-changed'));
    } catch (error) {
      notifications.show({ title: 'Unable to close shift', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <Card className="glass" withBorder radius="xl" p={64}><Group justify="center"><Loader /></Group></Card>;
  }

  const roleRequiresShift = Boolean(user.role?.requires_shift);
  const vehicleOptions = vehicles.results.map((row) => ({ value: String(row.id), label: String(row.name || `Vehicle #${row.id}`) }));

  return (
    <Stack gap="xl">
      <div>
        <Text size="sm" c="indigo.3" fw={800}>OPERATIONS</Text>
        <Title order={1} mt={4}>My shift</Title>
        <Text c="dimmed" mt={4}>{user.employee?.site ? `${user.employee.site.name} · ${user.employee.site.code}` : 'Your daily employee shift and settlement.'}</Text>
      </div>

      {shift?.status === 'open' ? (
        <>
          <Card className="glass" withBorder radius="lg" p="xl">
            <Group justify="space-between" align="flex-start">
              <div>
                <Text size="sm" fw={800}>Open shift</Text>
                <Text c="dimmed" size="sm" mt={4}>{shift.business_date} · {shift.site_name}</Text>
              </div>
              <Badge color="teal">OPEN</Badge>
            </Group>
            <SimpleGrid cols={{ base: 1, sm: 3 }} mt="xl">
              <div><Text size="xs" c="dimmed">Opening cash</Text><Text fw={800} size="lg">{formatMoney(shift.opening_cash)}</Text></div>
              <div><Text size="xs" c="dimmed">Vehicle</Text><Text fw={800}>{shift.vehicle_name || 'No vehicle assigned'}</Text></div>
              <div><Text size="xs" c="dimmed">Employee</Text><Text fw={800}>{shift.employee_name}</Text></div>
            </SimpleGrid>
          </Card>

          <Card className="glass" withBorder radius="lg" p="xl" maw={820}>
            <Stack>
              <div><Text fw={800}>Close shift</Text><Text c="dimmed" size="sm" mt={4}>Enter the amounts physically received at the end of the shift.</Text></div>
              <SimpleGrid cols={{ base: 1, sm: 2 }}>
                <NumberInput label="Actual cash" min={0} value={closingCash} onChange={setClosingCash} required />
                <NumberInput label="Actual transfer" min={0} value={closingTransfer} onChange={setClosingTransfer} required />
              </SimpleGrid>
              <Textarea label="Notes" value={closingNotes} onChange={(event) => setClosingNotes(event.currentTarget.value)} maxLength={500} />
              <Button loading={saving} onClick={close} color="dark">Close shift</Button>
            </Stack>
          </Card>
        </>
      ) : (
        <Card className="glass" withBorder radius="lg" p="xl" maw={820}>
          <Stack>
            <Group justify="space-between"><div><Text fw={800}>{shift ? 'Today is already closed' : 'No open shift today'}</Text><Text c="dimmed" size="sm" mt={4}>{roleRequiresShift ? 'Start your shift before creating operational transactions.' : 'You can open a shift when you need employee-level settlement tracking.'}</Text></div><Badge color={shift ? 'gray' : 'orange'}>{shift ? 'CLOSED' : 'NOT STARTED'}</Badge></Group>
            {!shift && (
              <>
                <NumberInput label="Opening cash" min={0} value={openingCash} onChange={setOpeningCash} required />
                <Select label="Assigned sales vehicle" placeholder={vehicleOptions.length ? 'Select a vehicle' : 'No active vehicles'} searchable clearable data={vehicleOptions} value={vehicle} onChange={(value) => setVehicle(value || '')} />
                <Button loading={saving} onClick={start}>Start shift</Button>
              </>
            )}
          </Stack>
        </Card>
      )}
    </Stack>
  );
}
