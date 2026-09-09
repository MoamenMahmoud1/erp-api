import { useEffect, useState } from 'react';
import { Badge, Button, Card, Group, Loader, Stack, Table, Text, Title } from '@mantine/core';
import { IconArrowRight, IconCreditCard, IconPackage, IconPlus, IconReceipt } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import { Link, useParams } from 'react-router-dom';

import { RecordsPage } from '../components/RecordsPage';
import { api } from '../lib/api';

function statusBadge(value: unknown) {
  const status = String(value || '').toUpperCase();
  const color = status.includes('PAID') || status.includes('CONFIRMED') || status.includes('CLOSED') ? 'teal' : status.includes('CANCEL') || status.includes('RETURN') ? 'red' : status.includes('OPEN') ? 'cyan' : 'gray';
  return <Badge color={color} variant="light">{String(value || '—').replaceAll('_', ' ')}</Badge>;
}

const draftOnly = (row: Record<string, unknown>) => String(row.status || '').toLowerCase() === 'draft';
const money = (value: unknown) => Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const dateTime = (value: unknown) => {
  if (!value) return '—';
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
};
const label = (value: unknown) => String(value || '—');

function invoiceDetails(data: Record<string, unknown>) {
  const items = Array.isArray(data.items) ? data.items as Record<string, unknown>[] : [];
  return (
    <Stack gap="lg">
      <div className="detail-grid">
        <div><Text size="xs" c="dimmed">Customer</Text><Text fw={700}>{label(data.customer_name)}</Text></div>
        <div><Text size="xs" c="dimmed">Salesperson</Text><Text fw={700}>{label(data.salesperson_name || data.created_by_name)}</Text></div>
        <div><Text size="xs" c="dimmed">Status</Text>{statusBadge(data.status)}</div>
        <div><Text size="xs" c="dimmed">Created</Text><Text fw={700}>{dateTime(data.created_at)}</Text></div>
      </div>
      <div className="metric-strip">
        <div><Text size="xs" c="dimmed">Subtotal</Text><Text fw={800}>{money(data.subtotal)}</Text></div>
        <div><Text size="xs" c="dimmed">Total</Text><Text fw={800}>{money(data.total)}</Text></div>
        <div><Text size="xs" c="dimmed">Gross profit</Text><Text fw={800}>{money(data.gross_profit)}</Text></div>
        <div><Text size="xs" c="dimmed">Outstanding</Text><Text fw={800}>{money(data.outstanding_amount)}</Text></div>
      </div>
      <div>
        <Text fw={800} mb="sm">Items</Text>
        <TableLike rows={items} fields={[['product_name', 'Product'], ['quantity', 'Qty'], ['unit_price', 'Unit price'], ['line_total', 'Total'], ['gross_profit', 'Profit']]} moneyFields={['unit_price', 'line_total', 'gross_profit']} />
      </div>
    </Stack>
  );
}

function purchaseDetails(data: Record<string, unknown>) {
  const items = Array.isArray(data.items) ? data.items as Record<string, unknown>[] : [];
  return (
    <Stack gap="lg">
      <div className="detail-grid">
        <div><Text size="xs" c="dimmed">Supplier</Text><Text fw={700}>{label(data.supplier_name)}</Text></div>
        <div><Text size="xs" c="dimmed">Status</Text>{statusBadge(data.status)}</div>
        <div><Text size="xs" c="dimmed">Reference</Text><Text fw={700}>{label(data.reference)}</Text></div>
        <div><Text size="xs" c="dimmed">Created</Text><Text fw={700}>{dateTime(data.created_at)}</Text></div>
      </div>
      <div className="metric-strip"><div><Text size="xs" c="dimmed">Total</Text><Text fw={800}>{money(data.total_amount)}</Text></div></div>
      <div>
        <Text fw={800} mb="sm">Received items</Text>
        <TableLike rows={items} fields={[['product_name', 'Product'], ['quantity', 'Qty'], ['unit_purchase_price', 'Unit cost'], ['total_amount', 'Total'], ['batch_number', 'Batch'], ['expiry_date', 'Expiry']]} moneyFields={['unit_purchase_price', 'total_amount']} />
      </div>
    </Stack>
  );
}

function paymentDetails(data: Record<string, unknown>) {
  const allocations = Array.isArray(data.allocations) ? data.allocations as Record<string, unknown>[] : [];
  const refunds = Array.isArray(data.refunds) ? data.refunds as Record<string, unknown>[] : [];
  return (
    <Stack gap="lg">
      <div className="detail-grid">
        <div><Text size="xs" c="dimmed">Customer</Text><Text fw={700}>{label(data.customer_name)}</Text></div>
        <div><Text size="xs" c="dimmed">Created</Text><Text fw={700}>{dateTime(data.created_at)}</Text></div>
        <div><Text size="xs" c="dimmed">Cash</Text><Text fw={700}>{money(data.cash_amount)}</Text></div>
        <div><Text size="xs" c="dimmed">Transfer</Text><Text fw={700}>{money(data.transfer_amount)}</Text></div>
      </div>
      <div className="metric-strip">
        <div><Text size="xs" c="dimmed">Total</Text><Text fw={800}>{money(data.total_amount)}</Text></div>
        <div><Text size="xs" c="dimmed">Refunded</Text><Text fw={800}>{money(data.refunded_amount)}</Text></div>
        <div><Text size="xs" c="dimmed">Refundable</Text><Text fw={800}>{money(data.refundable_amount)}</Text></div>
      </div>
      <div>
        <Text fw={800} mb="sm">Invoice allocations</Text>
        <TableLike rows={allocations} fields={[['invoice_number', 'Invoice'], ['cash_amount', 'Cash'], ['transfer_amount', 'Transfer'], ['total_amount', 'Total']]} moneyFields={['cash_amount', 'transfer_amount', 'total_amount']} fallbackFields={{ invoice_number: 'invoice' }} />
      </div>
      {refunds.length > 0 && <div><Text fw={800} mb="sm">Refunds</Text><TableLike rows={refunds} fields={[['invoice_number', 'Invoice'], ['total_amount', 'Refund'], ['reason', 'Reason'], ['created_at', 'Date']]} moneyFields={['total_amount']} fallbackFields={{ invoice_number: 'invoice' }} dateFields={['created_at']} /></div>}
    </Stack>
  );
}

function TableLike({ rows, fields, moneyFields, fallbackFields = {}, dateFields = [] }: { rows: Record<string, unknown>[]; fields: [string, string][]; moneyFields: string[]; fallbackFields?: Record<string, string>; dateFields?: string[] }) {
  if (!rows.length) return <Text size="sm" c="dimmed">No records.</Text>;
  return (
    <div className="detail-table-wrap">
      <table className="detail-table">
        <thead><tr>{fields.map(([, fieldLabel]) => <th key={fieldLabel}>{fieldLabel}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={String(row.id ?? index)}>
              {fields.map(([key]) => {
                const raw = row[key] ?? (fallbackFields[key] ? row[fallbackFields[key]] : undefined);
                const rendered = dateFields.includes(key) ? dateTime(raw) : moneyFields.includes(key) ? money(raw) : label(raw);
                return <td key={key}>{rendered}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DetailPage({ kind, id, load, eyebrow, titlePrefix, render }: { kind: string; id: string | undefined; load: (id: number) => Promise<unknown>; eyebrow: string; titlePrefix: string; render: (data: Record<string, unknown>) => React.ReactNode }) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const value = Number(id);
    if (!Number.isInteger(value) || value <= 0) {
      setLoading(false);
      notifications.show({ title: `Invalid ${kind}`, message: `The requested ${kind.toLowerCase()} number is invalid.`, color: 'red' });
      return;
    }
    load(value)
      .then((result) => setData(result as Record<string, unknown>))
      .catch((error) => notifications.show({ title: `${kind} unavailable`, message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }))
      .finally(() => setLoading(false));
  }, [id, kind, load]);

  if (loading) return <Card className="glass" radius="xl" p={60} withBorder><Group justify="center"><Loader /></Group></Card>;
  if (!data) return <Card className="glass" radius="xl" p="xl" withBorder><Text fw={800}>{kind} unavailable</Text><Text c="dimmed" mt="xs">The {kind.toLowerCase()} could not be loaded.</Text></Card>;
  return (
    <Stack gap="xl">
      <Group justify="space-between" align="flex-end" wrap="wrap">
        <div><Text size="sm" c="indigo.3" fw={800}>{eyebrow}</Text><Title order={1} mt={4}>{titlePrefix} #{String(data.id)}</Title></div>
        <Button component={Link} to={kind === 'Invoice' ? '/sales' : kind === 'Purchase' ? '/purchases' : '/payments'} variant="subtle" rightSection={<IconArrowRight size={15} />}>Back to {kind === 'Invoice' ? 'sales' : kind === 'Purchase' ? 'purchases' : 'payments'}</Button>
      </Group>
      <Card className="glass" radius="xl" withBorder p="xl">{render(data)}</Card>
    </Stack>
  );
}

export function InvoiceDetailsPage() {
  const { id } = useParams();
  return <DetailPage kind="Invoice" id={id} load={api.invoices.get} eyebrow="SALES" titlePrefix="Invoice" render={invoiceDetails} />;
}

export function PurchaseDetailsPage() {
  const { id } = useParams();
  return <DetailPage kind="Purchase" id={id} load={api.purchases.get} eyebrow="PURCHASING" titlePrefix="Purchase" render={purchaseDetails} />;
}

export function PaymentDetailsPage() {
  const { id } = useParams();
  const load = async (paymentId: number) => {
    const result = await api.payments.transactions(`?id=${paymentId}&page_size=1`);
    return result.results[0] || null;
  };
  return <DetailPage kind="Payment" id={id} load={load} eyebrow="PAYMENTS" titlePrefix="Payment" render={paymentDetails} />;
}

const linkButton = (to: string, labelText: string, icon: React.ReactNode) => <Button component={Link} to={to} leftSection={icon} radius="lg">{labelText}</Button>;

export function SalesPage() {
  return (
    <RecordsPage
      eyebrow="COMMAND CENTER"
      title="Sales"
      subtitle="Search, review and confirm customer invoices without leaving the sales workspace."
      searchPlaceholder="Search invoices by customer, salesperson or reference…"
      topContent={linkButton('/sales/new', 'New sale', <IconPlus size={16} />)}
      list={api.invoices.list}
      details={{ load: api.invoices.get, render: invoiceDetails }}
      columns={[
        { key: 'id', label: '#' },
        { key: 'customer_name', label: 'Customer' },
        { key: 'salesperson_name', label: 'Salesperson' },
        { key: 'status', label: 'Status', format: statusBadge },
        { key: 'total', label: 'Total', format: money },
        { key: 'paid_amount', label: 'Paid', format: money },
        { key: 'outstanding_amount', label: 'Outstanding', format: money },
        { key: 'created_at', label: 'Created', format: dateTime },
      ]}
      actions={[
        { label: 'Confirm', color: 'teal', visible: draftOnly, confirm: 'Confirm this invoice? This will post the sale and affect inventory/accounting.', run: (row) => api.invoices.confirm(Number(row.id)) },
        { label: 'Cancel', color: 'red', visible: draftOnly, confirm: 'Cancel this draft invoice?', run: (row) => api.invoices.cancel(Number(row.id)) },
      ]}
    />
  );
}

export function PurchasesPage() {
  return (
    <RecordsPage
      eyebrow="COMMAND CENTER"
      title="Purchases"
      subtitle="Track supplier purchases, receiving batches and confirmation workflow."
      searchPlaceholder="Search purchases by supplier, reference or status…"
      topContent={linkButton('/purchases/new', 'New purchase', <IconPlus size={16} />)}
      list={api.purchases.list}
      details={{ load: api.purchases.get, render: purchaseDetails }}
      columns={[
        { key: 'id', label: '#' },
        { key: 'supplier_name', label: 'Supplier' },
        { key: 'status', label: 'Status', format: statusBadge },
        { key: 'total_amount', label: 'Total', format: money },
        { key: 'reference', label: 'Reference' },
        { key: 'created_at', label: 'Created', format: dateTime },
      ]}
      actions={[
        { label: 'Confirm', color: 'teal', visible: draftOnly, confirm: 'Confirm this purchase? It will receive stock into inventory.', run: (row) => api.purchases.confirm(Number(row.id)) },
        { label: 'Cancel', color: 'red', visible: draftOnly, confirm: 'Cancel this draft purchase?', run: (row) => api.purchases.cancel(Number(row.id)) },
      ]}
    />
  );
}

export function PaymentsPage() {
  return (
    <RecordsPage
      eyebrow="OPERATIONS"
      title="Payments"
      subtitle="Collections, refunds and payment transaction history."
      searchPlaceholder="Search payments by customer or reference…"
      topContent={<Group gap="xs"><Button component={Link} to="/payments/collect" leftSection={<IconCreditCard size={16} />} radius="lg">Collect</Button><Button component={Link} to="/payments/supplier" variant="light" leftSection={<IconTruckFallback />} radius="lg">Pay supplier</Button></Group>}
      list={api.payments.transactions}
      details={{ load: async (id) => { const result = await api.payments.transactions(`?id=${id}&page_size=1`); return result.results[0] || null; }, render: paymentDetails }}
      columns={[{ key: 'id', label: '#' }, { key: 'customer_name', label: 'Customer' }, { key: 'total_amount', label: 'Amount', format: money }, { key: 'cash_amount', label: 'Cash', format: money }, { key: 'transfer_amount', label: 'Bank / transfer', format: money }, { key: 'created_at', label: 'Date', format: dateTime }]}
    />
  );
}

function IconTruckFallback() {
  return <IconPackage size={16} />;
}

export function InventoryPage() {
  return (
    <RecordsPage
      eyebrow="OPERATIONS"
      title="Inventory"
      subtitle="Live stock balances by product and location. Use movements and transfer for stock operations."
      searchPlaceholder="Search inventory by product or location…"
      topContent={linkButton('/inventory/transfer', 'Transfer stock', <IconPackage size={16} />)}
      list={api.inventory.stock}
      details={{ load: async (id) => { const result = await api.inventory.stock(`?id=${id}&page_size=1`); return result.results[0] || null; } }}
      columns={[{ key: 'id', label: '#' }, { key: 'product_name', label: 'Product' }, { key: 'location_name', label: 'Location' }, { key: 'quantity', label: 'Quantity', format: (value) => Number(value || 0).toLocaleString() }, { key: 'updated_at', label: 'Updated', format: dateTime }]}
    />
  );
}
