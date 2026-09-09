import type { FormEvent } from 'react';
import { useEffect, useState } from 'react';
import { Badge, Button, Card, Group, Loader, NumberInput, Select, Stack, Text, TextInput, Title } from '@mantine/core';
import { IconArrowRight, IconPackage } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';

import { RecordsPage } from '../components/RecordsPage';
import { api, type Paginated } from '../lib/api';

export function InventoryLocationsPage() {
  return (
    <RecordsPage
      eyebrow="INVENTORY"
      title="Locations"
      subtitle="Sales vehicles and warehouses organized by branch or store."
      searchPlaceholder="Search locations by name, site or employee…"
      list={api.inventory.locations}
      columns={[
        { key: 'id', label: '#' },
        { key: 'site_name', label: 'Branch / store' },
        { key: 'name', label: 'Location' },
        { key: 'location_type', label: 'Type', format: (value) => <Badge variant="light">{String(value || '—').replaceAll('_', ' ')}</Badge> },
        { key: 'employee_name', label: 'Assigned employee' },
        { key: 'is_active', label: 'Status' },
        { key: 'created_at', label: 'Created' },
      ]}
    />
  );
}

export function InventoryMovementsPage() {
  return (
    <RecordsPage
      eyebrow="INVENTORY"
      title="Movements"
      subtitle="Stock transfers and movements across branches, stores and locations."
      searchPlaceholder="Search movements by reference, product, location or employee…"
      list={api.inventory.movements}
      columns={[
        { key: 'id', label: '#' },
        { key: 'movement_type', label: 'Type', format: (value) => String(value || '—').replaceAll('_', ' ') },
        { key: 'source_site_name', label: 'From branch' },
        { key: 'source_location_name', label: 'From location' },
        { key: 'destination_site_name', label: 'To branch' },
        { key: 'destination_location_name', label: 'To location' },
        { key: 'created_by_name', label: 'Created by' },
        { key: 'reference', label: 'Reference' },
        { key: 'created_at', label: 'Date' },
      ]}
    />
  );
}

export function InventoryTransferPage() {
  const [locations, setLocations] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [sourceStock, setSourceStock] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [source, setSource] = useState('');
  const [destination, setDestination] = useState('');
  const [product, setProduct] = useState('');
  const [quantity, setQuantity] = useState<number | string>(1);
  const [reference, setReference] = useState('');
  const [loadingLocations, setLoadingLocations] = useState(true);
  const [loadingStock, setLoadingStock] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoadingLocations(true);
    api.inventory.locations('?page_size=100')
      .then(setLocations)
      .catch((error) => notifications.show({ title: 'Unable to load locations', message: error instanceof Error ? error.message : 'Check the API and your permissions.', color: 'red' }))
      .finally(() => setLoadingLocations(false));
  }, []);

  useEffect(() => {
    setProduct('');
    setSourceStock({ count: 0, next: null, previous: null, results: [] });
    if (!source) return;
    setLoadingStock(true);
    api.inventory.stock(`?location=${source}&page_size=100`)
      .then(setSourceStock)
      .catch((error) => notifications.show({ title: 'Unable to load source stock', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }))
      .finally(() => setLoadingStock(false));
  }, [source]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!source || !destination || !product || Number(quantity) < 1 || source === destination) return;
    const selected = sourceStock.results.find((item) => String(item.product) === product);
    if (!selected || Number(quantity) > Number(selected.quantity || 0)) {
      notifications.show({ title: 'Insufficient source stock', message: 'Reduce the quantity or choose another product.', color: 'red' });
      return;
    }
    setLoading(true);
    try {
      await api.inventory.transfer({
        source_location: Number(source),
        destination_location: Number(destination),
        reference,
        items: [{ product: Number(product), quantity: Number(quantity) }],
      });
      notifications.show({ title: 'Transfer completed', message: 'Stock movement recorded successfully.', color: 'teal' });
      setSource(''); setDestination(''); setProduct(''); setQuantity(1); setReference('');
    } catch (error) {
      notifications.show({ title: 'Transfer failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    } finally {
      setLoading(false);
    }
  }

  const locationOptions = locations.results.map((item) => ({
    value: String(item.id),
    label: `${item.site_name || 'Unassigned site'} · ${item.name || 'Unnamed location'} · ${String(item.location_type || 'location').replaceAll('_', ' ')}`,
  }));
  const productOptions = sourceStock.results
    .filter((item) => Number(item.quantity || 0) > 0)
    .map((item) => ({ value: String(item.product), label: `${item.product_name || `Product #${item.product}`} · ${Number(item.quantity || 0).toLocaleString()} available` }));
  const selectedProduct = sourceStock.results.find((item) => String(item.product) === product);
  const available = Number(selectedProduct?.quantity || 0);

  return (
    <Stack gap="xl">
      <div>
        <Text size="sm" c="indigo.3" fw={800} tt="uppercase" lts=".08em">INVENTORY</Text>
        <Title order={1} mt={4}>Transfer stock</Title>
        <Text c="dimmed" mt={4}>Move inventory between two locations with one atomic operation.</Text>
      </div>
      <Card className="glass bento-card" radius="xl" withBorder p={{ base: 'md', sm: 'xl' }} maw={820}>
        <form onSubmit={submit}>
          <Stack>
            <Select
              label="Source location"
              description="Only stock actually available here can be selected."
              data={locationOptions}
              value={source}
              onChange={(value) => setSource(value || '')}
              searchable
              required
              disabled={loadingLocations}
              rightSection={loadingLocations ? <Loader size="xs" /> : undefined}
            />
            <Select
              label="Destination location"
              description="Cannot be the same as the source."
              data={locationOptions.filter((item) => item.value !== source)}
              value={destination}
              onChange={(value) => setDestination(value || '')}
              searchable
              required
              disabled={!source || loadingLocations}
            />
            <Select
              label="Product"
              description={source ? 'Showing products with stock in the selected source location.' : 'Select a source location first.'}
              data={productOptions}
              value={product}
              onChange={(value) => { setProduct(value || ''); setQuantity(1); }}
              searchable
              required
              disabled={!source || loadingStock}
              rightSection={loadingStock ? <Loader size="xs" /> : undefined}
              nothingFoundMessage={source ? 'No available stock in this location.' : 'Select a source first.'}
            />
            {product && <Card withBorder radius="lg" p="sm" bg="transparent"><Group justify="space-between"><Text size="sm" c="dimmed">Available at source</Text><Text fw={850}>{available.toLocaleString()} units</Text></Group></Card>}
            <NumberInput label="Quantity" description={product ? `Maximum ${available.toLocaleString()} units` : undefined} min={1} max={available || undefined} value={quantity} onChange={setQuantity} required disabled={!product} />
            <TextInput label="Reference" value={reference} onChange={(event) => setReference(event.currentTarget.value)} placeholder="Optional transfer reference" />
            <Button type="submit" loading={loading} disabled={!source || !destination || !product || source === destination || available < 1 || Number(quantity) > available} leftSection={<IconArrowRight size={17} />} variant="gradient" gradient={{ from: 'indigo', to: 'cyan', deg: 120 }}>
              Transfer stock
            </Button>
          </Stack>
        </form>
      </Card>
    </Stack>
  );
}
