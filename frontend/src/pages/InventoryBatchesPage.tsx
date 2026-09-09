import { Badge } from '@mantine/core';

import { RecordsPage } from '../components/RecordsPage';
import { api } from '../lib/api';

function expiryBadge(value: unknown, days: unknown) {
  if (value === true) return <Badge color="red" variant="light">Expired</Badge>;
  const remaining = Number(days);
  if (Number.isFinite(remaining) && remaining <= 7) return <Badge color="orange" variant="light">{remaining}d left</Badge>;
  if (Number.isFinite(remaining)) return <Badge color="teal" variant="light">{remaining}d left</Badge>;
  return <Badge variant="light">No expiry</Badge>;
}

export function InventoryBatchesPage() {
  return (
    <RecordsPage
      eyebrow="INVENTORY"
      title="Batches & expiry"
      subtitle="Trace received lots, production dates, expiry dates and the quantity still available at each location."
      list={api.inventory.batches}
      columns={[
        { key: 'product_name', label: 'Product' },
        { key: 'batch_number', label: 'Batch / lot', format: (value) => String(value || 'Unnumbered') },
        { key: 'location_name', label: 'Location' },
        { key: 'quantity', label: 'Qty' },
        { key: 'manufactured_date', label: 'Manufactured' },
        { key: 'expiry_date', label: 'Expiry' },
        { key: 'is_expired', label: 'Status', format: (value, row) => expiryBadge(value, row.days_to_expiry) },
        { key: 'average_unit_cost', label: 'Unit cost' },
        { key: 'total_cost', label: 'Inventory value' },
      ]}
    />
  );
}
