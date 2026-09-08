import { Badge } from '@mantine/core';

import { RecordsPage } from '../components/RecordsPage';
import { api } from '../lib/api';

function statusBadge(value: unknown) {
  const status = String(value || '').toUpperCase();
  const color = status.includes('PAID') || status.includes('CONFIRMED') ? 'teal' : status.includes('CANCEL') || status.includes('RETURN') ? 'red' : 'gray';
  return <Badge color={color} variant="light">{String(value || '—')}</Badge>;
}

const draftOnly = (row: Record<string, unknown>) => row.status === 'draft';

export function SalesPage() {
  return (
    <RecordsPage
      eyebrow="COMMAND CENTER"
      title="Sales"
      subtitle="Invoice pipeline with draft-only confirmation and cancellation actions."
      list={api.invoices.list}
      columns={[
        { key: 'id', label: '#' },
        { key: 'customer_name', label: 'Customer' },
        { key: 'status', label: 'Status', format: statusBadge },
        { key: 'total', label: 'Total' },
        { key: 'paid_amount', label: 'Paid' },
        { key: 'outstanding_amount', label: 'Outstanding' },
        { key: 'created_at', label: 'Created' },
      ]}
      actions={[
        { label: 'Confirm', color: 'teal', visible: draftOnly, run: (row) => api.invoices.confirm(Number(row.id)) },
        { label: 'Cancel', color: 'red', visible: draftOnly, run: (row) => api.invoices.cancel(Number(row.id)) },
      ]}
    />
  );
}

export function PurchasesPage() {
  return (
    <RecordsPage
      eyebrow="COMMAND CENTER"
      title="Purchases"
      subtitle="Purchase orders, supplier obligations and receiving workflow."
      list={api.purchases.list}
      columns={[
        { key: 'id', label: '#' },
        { key: 'supplier_name', label: 'Supplier' },
        { key: 'status', label: 'Status', format: statusBadge },
        { key: 'total_amount', label: 'Total' },
        { key: 'created_at', label: 'Created' },
        { key: 'reference', label: 'Reference' },
      ]}
      actions={[
        { label: 'Confirm', color: 'teal', visible: draftOnly, run: (row) => api.purchases.confirm(Number(row.id)) },
        { label: 'Cancel', color: 'red', visible: draftOnly, run: (row) => api.purchases.cancel(Number(row.id)) },
      ]}
    />
  );
}

export function PaymentsPage() {
  return (
    <RecordsPage
      eyebrow="OPERATIONS"
      title="Payments"
      subtitle="Collections, refunds and transaction history."
      list={api.payments.transactions}
      columns={[
        { key: 'id', label: '#' },
        { key: 'customer_name', label: 'Customer' },
        { key: 'total_amount', label: 'Amount' },
        { key: 'cash_amount', label: 'Cash' },
        { key: 'transfer_amount', label: 'Bank / transfer' },
        { key: 'created_at', label: 'Date' },
      ]}
    />
  );
}

export function InventoryPage() {
  return (
    <RecordsPage
      eyebrow="OPERATIONS"
      title="Inventory"
      subtitle="Live stock, movement history and warehouse locations."
      list={api.inventory.stock}
      columns={[
        { key: 'id', label: '#' },
        { key: 'product_name', label: 'Product' },
        { key: 'location_name', label: 'Location' },
        { key: 'quantity', label: 'Quantity' },
        { key: 'updated_at', label: 'Updated' },
      ]}
    />
  );
}
