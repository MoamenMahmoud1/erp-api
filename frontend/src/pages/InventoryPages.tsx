import type { FormEvent } from 'react';
import { useEffect, useState } from 'react';
import { Badge, Button, Card, Group, NumberInput, Select, Stack, Text, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';

import { RecordsPage } from '../components/RecordsPage';
import { api, type Paginated } from '../lib/api';

export function InventoryLocationsPage() {
  return <RecordsPage eyebrow="INVENTORY" title="Locations" subtitle="Sales vehicles, warehouses and active stock locations." list={api.inventory.locations} columns={[{ key: 'id', label: '#' }, { key: 'name', label: 'Location' }, { key: 'location_type', label: 'Type', format: (value) => <Badge variant="light">{String(value).replaceAll('_', ' ')}</Badge> }, { key: 'employee_name', label: 'Assigned employee' }, { key: 'is_active', label: 'Status' }, { key: 'created_at', label: 'Created' }]} />;
}

export function InventoryMovementsPage() {
  return <RecordsPage eyebrow="INVENTORY" title="Movements" subtitle="Immutable stock movement history." list={api.inventory.movements} columns={[{ key: 'id', label: '#' }, { key: 'movement_type', label: 'Type' }, { key: 'source_location_name', label: 'From' }, { key: 'destination_location_name', label: 'To' }, { key: 'created_by_name', label: 'Created by' }, { key: 'reference', label: 'Reference' }, { key: 'created_at', label: 'Date' }]} />;
}

export function InventoryTransferPage() {
  const [locations, setLocations] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [products, setProducts] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [source, setSource] = useState('');
  const [destination, setDestination] = useState('');
  const [product, setProduct] = useState('');
  const [quantity, setQuantity] = useState<number | string>(1);
  const [reference, setReference] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Promise.all([api.inventory.locations('?page_size=50'), api.products.list('?page_size=50')])
      .then(([locationsResult, productsResult]) => { setLocations(locationsResult); setProducts(productsResult); })
      .catch(() => notifications.show({ title: 'Unable to load transfer options', message: 'Check the API and your permissions.', color: 'red' }));
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!source || !destination || !product || Number(quantity) < 1 || source === destination) return;
    setLoading(true);
    try {
      await api.inventory.transfer({ source_location: Number(source), destination_location: Number(destination), reference, items: [{ product: Number(product), quantity: Number(quantity) }] });
      notifications.show({ title: 'Transfer completed', message: 'Stock movement recorded successfully.', color: 'teal' });
      setSource(''); setDestination(''); setProduct(''); setQuantity(1); setReference('');
    } catch (error) {
      notifications.show({ title: 'Transfer failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    } finally { setLoading(false); }
  }

  const locationOptions = locations.results.map((item) => ({ value: String(item.id), label: `${item.name || 'Unnamed location'} · ${String(item.location_type || 'location').replaceAll('_', ' ')}` }));
  const productOptions = products.results.map((item) => ({ value: String(item.id), label: `${item.name || 'Unnamed product'} · stock ${item.stock_quantity ?? '—'}` }));

  return <Stack gap="xl"><div><Text size="sm" c="indigo.3" fw={800}>INVENTORY</Text><Title order={1} mt={4}>Transfer stock</Title><Text c="dimmed" mt={4}>Move inventory between two locations with one atomic operation.</Text></div><Card className="glass bento-card" radius="lg" withBorder p="xl" maw={820}><form onSubmit={submit}><Stack><Select label="Source location" data={locationOptions} value={source} onChange={(value) => setSource(value || '')} searchable required /><Select label="Destination location" data={locationOptions.filter((item) => item.value !== source)} value={destination} onChange={(value) => setDestination(value || '')} searchable required /><Select label="Product" data={productOptions} value={product} onChange={(value) => setProduct(value || '')} searchable required /><NumberInput label="Quantity" min={1} value={quantity} onChange={setQuantity} required /><TextInput label="Reference" value={reference} onChange={(event) => setReference(event.currentTarget.value)} placeholder="Optional" /><Button type="submit" loading={loading} disabled={!source || !destination || !product || source === destination} variant="gradient" gradient={{ from: 'indigo', to: 'cyan', deg: 120 }}>Transfer stock</Button></Stack></form></Card></Stack>;
}
