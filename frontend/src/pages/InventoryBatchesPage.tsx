import { Badge } from '@mantine/core';

import { RecordsPage } from '../components/RecordsPage';
import { api } from '../lib/api';

function expiryBadge(value: unknown, days: unknown) {
  if (value === true) return <Badge color="red" variant="light">Expired</Badge>;
  const remaining = Number(days);
  if (!Number.isFinite(remaining)) return <Badge variant="light">No expiry</Badge>;
  if (remaining < 0) return <Badge color="red" variant="light">Expired</Badge>;
  if (remaining === 0) return <Badge color="orange" variant="light">Expires today</Badge>;
  if (remaining <= 7) return <Badge color="orange" variant="light">{remaining}d left</Badge>;
  if (remaining <= 30) return <Badge color="yellow" variant="light">{remaining}d left</Badge>;
  return <Badge color="teal" variant="light">{remaining}d left</Badge>;
}

const dateOnly = (value: unknown) => {
  if (!value) return '—';
  const raw = String(value);
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw);
  const date = match
    ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
    : new Date(raw);
  return Number.isNaN(date.getTime()) ? raw : date.toLocaleDateString([], { dateStyle: 'medium' });
};

export function InventoryBatchesPage() {
  return (
    <RecordsPage
      eyebrow="INVENTORY"
      title="Batches & expiry"
      subtitle="Trace received lots, production dates, expiry dates and quantity still available at each location."
      searchPlaceholder="Search by product, batch or location…"
      list={api.inventory.batches}
      columns={[
        { key: 'product_name', label: 'Product' },
        { key: 'batch_number', label: 'Batch / lot', format: (value) => String(value || 'Unnumbered') },
        { key: 'location_name', label: 'Location' },
        { key: 'quantity', label: 'Qty', format: (value) => Number(value || 0).toLocaleString() },
        { key: 'manufactured_date', label: 'Manufactured', format: dateOnly },
        { key: 'expiry_date', label: 'Expiry', format: dateOnly },
        { key: 'is_expired', label: 'Status', format: (value, row) => expiryBadge(value, row.days_to_expiry) },
        { key: 'average_unit_cost', label: 'Unit cost' },
        { key: 'total_cost', label: 'Inventory value' },
      ]}
    />
  );
}
