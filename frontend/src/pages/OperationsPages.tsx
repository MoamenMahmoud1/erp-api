import { useEffect, useState } from 'react';
import { Badge, Button, Card, Group, Loader, Stack, Table, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useParams } from 'react-router-dom';

import { RecordsPage } from '../components/RecordsPage';
import { api } from '../lib/api';

function statusBadge(value: unknown) {
  const status = String(value || '').toUpperCase();
  const color = status.includes('PAID') || status.includes('CONFIRMED') ? 'teal' : status.includes('CANCEL') || status.includes('RETURN') ? 'red' : 'gray';
  return <Badge color={color} variant="light">{String(value || '—')}</Badge>;
}

const draftOnly = (row: Record<string, unknown>) => String(row.status || '').toLowerCase() === 'draft';
const money = (value: unknown) => Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function invoiceDetails(data: Record<string, unknown>) {
  const items = Array.isArray(data.items) ? data.items as Record<string, unknown>[] : [];
  return <div style={{ display: 'grid', gap: 16 }}><div><b>Customer:</b> {String(data.customer_name || '—')}</div><div><b>Salesperson:</b> {String(data.salesperson_name || data.created_by_name || '—')}</div><div><b>Status:</b> {String(data.status || '—')}</div><div><b>Subtotal:</b> {money(data.subtotal)} &nbsp; <b>Total:</b> {money(data.total)} &nbsp; <b>Gross profit:</b> {money(data.gross_profit)}</div><div><b>Paid:</b> {money(data.net_paid_amount)} &nbsp; <b>Outstanding:</b> {money(data.outstanding_amount)} &nbsp; <b>Returned:</b> {money(data.returned_amount)}</div><div><b>Created:</b> {String(data.created_at || '—')}</div><div><b>Items</b><TableLike rows={items} fields={[['product_name', 'Product'], ['quantity', 'Qty'], ['unit_price', 'Unit price'], ['line_total', 'Total'], ['gross_profit', 'Profit']]} moneyFields={['unit_price', 'line_total', 'gross_profit']} /></div></div>;
}

function purchaseDetails(data: Record<string, unknown>) {
  const items = Array.isArray(data.items) ? data.items as Record<string, unknown>[] : [];
  return <div style={{ display: 'grid', gap: 16 }}><div><b>Supplier:</b> {String(data.supplier_name || '—')}</div><div><b>Status:</b> {String(data.status || '—')}</div><div><b>Reference:</b> {String(data.reference || '—')}</div><div><b>Total:</b> {money(data.total_amount)} &nbsp; <b>Created:</b> {String(data.created_at || '—')}</div><div><b>Items</b><TableLike rows={items} fields={[['product_name', 'Product'], ['quantity', 'Qty'], ['unit_purchase_price', 'Unit cost'], ['total_amount', 'Total']]} moneyFields={['unit_purchase_price', 'total_amount']} /></div></div>;
}

function paymentDetails(data: Record<string, unknown>) {
  const allocations = Array.isArray(data.allocations) ? data.allocations as Record<string, unknown>[] : [];
  const refunds = Array.isArray(data.refunds) ? data.refunds as Record<string, unknown>[] : [];
  return <div style={{ display: 'grid', gap: 16 }}><div><b>Customer:</b> {String(data.customer_name || '—')}</div><div><b>Total:</b> {money(data.total_amount)} &nbsp; <b>Refunded:</b> {money(data.refunded_amount)} &nbsp; <b>Refundable:</b> {money(data.refundable_amount)}</div><div><b>Cash:</b> {money(data.cash_amount)} &nbsp; <b>Transfer:</b> {money(data.transfer_amount)}</div><div><b>Invoice allocations</b><TableLike rows={allocations} fields={[['invoice', 'Invoice'], ['cash_amount', 'Cash'], ['transfer_amount', 'Transfer'], ['total_amount', 'Total']]} moneyFields={['cash_amount', 'transfer_amount', 'total_amount']} /></div>{refunds.length > 0 && <div><b>Refunds</b><TableLike rows={refunds} fields={[['invoice', 'Invoice'], ['total_amount', 'Refund'], ['reason', 'Reason'], ['created_at', 'Date']]} moneyFields={['total_amount']} /></div>}</div>;
}

function TableLike({ rows, fields, moneyFields }: { rows: Record<string, unknown>[]; fields: [string, string][]; moneyFields: string[] }) {
  return <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 8 }}><thead><tr>{fields.map(([, label]) => <th key={label} style={{ textAlign: 'left', padding: 8 }}>{label}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={String(row.id ?? index)}>{fields.map(([key]) => <td key={key} style={{ padding: 8 }}>{moneyFields.includes(key) ? money(row[key]) : String(row[key] ?? '—')}</td>)}</tr>)}</tbody></table></div>;
}

export function InvoiceDetailsPage() {
  const { id } = useParams();
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const invoiceId = Number(id);
    if (!Number.isInteger(invoiceId) || invoiceId <= 0) { setLoading(false); notifications.show({ title: 'Invalid invoice', message: 'The requested invoice number is invalid.', color: 'red' }); return; }
    api.invoices.get(invoiceId).then((result) => setData(result as Record<string, unknown>)).catch((error) => notifications.show({ title: 'Invoice unavailable', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' })).finally(() => setLoading(false));
  }, [id]);
  if (loading) return <Card className="glass" radius="xl" p={60} withBorder><Group justify="center"><Loader /></Group></Card>;
  if (!data) return <Card className="glass" radius="xl" p="xl" withBorder><Text fw={800}>Invoice unavailable</Text><Text c="dimmed" mt="xs">The invoice could not be loaded.</Text></Card>;
  return <Stack gap="xl"><div><Text size="sm" c="indigo.3" fw={800}>SALES</Text><Title order={1} mt={4}>Invoice #{String(data.id)}</Title></div><Card className="glass" radius="xl" withBorder p="xl">{invoiceDetails(data)}</Card></Stack>;
}

export function PurchaseDetailsPage() {
  const { id } = useParams();
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const purchaseId = Number(id);
    if (!Number.isInteger(purchaseId) || purchaseId <= 0) { setLoading(false); notifications.show({ title: 'Invalid purchase', message: 'The requested purchase number is invalid.', color: 'red' }); return; }
    api.purchases.get(purchaseId).then((result) => setData(result as Record<string, unknown>)).catch((error) => notifications.show({ title: 'Purchase unavailable', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' })).finally(() => setLoading(false));
  }, [id]);
  if (loading) return <Card className="glass" radius="xl" p={60} withBorder><Group justify="center"><Loader /></Group></Card>;
  if (!data) return <Card className="glass" radius="xl" p="xl" withBorder><Text fw={800}>Purchase unavailable</Text><Text c="dimmed" mt="xs">The purchase could not be loaded.</Text></Card>;
  return <Stack gap="xl"><div><Text size="sm" c="indigo.3" fw={800}>PURCHASING</Text><Title order={1} mt={4}>Purchase #{String(data.id)}</Title></div><Card className="glass" radius="xl" withBorder p="xl">{purchaseDetails(data)}</Card></Stack>;
}

export function PaymentDetailsPage() {
  const { id } = useParams();
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const paymentId = Number(id);
    if (!Number.isInteger(paymentId) || paymentId <= 0) { setLoading(false); notifications.show({ title: 'Invalid payment', message: 'The requested payment number is invalid.', color: 'red' }); return; }
    api.payments.transactions(`?id=${paymentId}&page_size=1`).then((result) => setData(result.results[0] || null)).catch((error) => notifications.show({ title: 'Payment unavailable', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' })).finally(() => setLoading(false));
  }, [id]);
  if (loading) return <Card className="glass" radius="xl" p={60} withBorder><Group justify="center"><Loader /></Group></Card>;
  if (!data) return <Card className="glass" radius="xl" p="xl" withBorder><Text fw={800}>Payment unavailable</Text><Text c="dimmed" mt="xs">The payment could not be loaded.</Text></Card>;
  return <Stack gap="xl"><div><Text size="sm" c="indigo.3" fw={800}>PAYMENTS</Text><Title order={1} mt={4}>Payment #{String(data.id)}</Title></div><Card className="glass" radius="xl" withBorder p="xl">{paymentDetails(data)}</Card></Stack>;
}

export function SalesPage() {
  return <RecordsPage eyebrow="COMMAND CENTER" title="Sales" subtitle="Invoice pipeline with draft-only confirmation and cancellation actions." list={api.invoices.list} details={{ load: api.invoices.get, render: invoiceDetails }} columns={[{ key: 'id', label: '#' }, { key: 'customer_name', label: 'Customer' }, { key: 'salesperson_name', label: 'Salesperson' }, { key: 'status', label: 'Status', format: statusBadge }, { key: 'total', label: 'Total' }, { key: 'paid_amount', label: 'Paid' }, { key: 'outstanding_amount', label: 'Outstanding' }, { key: 'created_at', label: 'Created' }]} actions={[{ label: 'Confirm', color: 'teal', visible: draftOnly, run: (row) => api.invoices.confirm(Number(row.id)) }, { label: 'Cancel', color: 'red', visible: draftOnly, run: (row) => api.invoices.cancel(Number(row.id)) }]} />;
}

export function PurchasesPage() {
  return <RecordsPage eyebrow="COMMAND CENTER" title="Purchases" subtitle="Purchase orders, supplier obligations and receiving workflow." list={api.purchases.list} details={{ load: api.purchases.get, render: purchaseDetails }} columns={[{ key: 'id', label: '#' }, { key: 'supplier_name', label: 'Supplier' }, { key: 'status', label: 'Status', format: statusBadge }, { key: 'total_amount', label: 'Total' }, { key: 'created_at', label: 'Created' }, { key: 'reference', label: 'Reference' }]} actions={[{ label: 'Confirm', color: 'teal', visible: draftOnly, run: (row) => api.purchases.confirm(Number(row.id)) }, { label: 'Cancel', color: 'red', visible: draftOnly, run: (row) => api.purchases.cancel(Number(row.id)) }]} />;
}

export function PaymentsPage() {
  return <RecordsPage eyebrow="OPERATIONS" title="Payments" subtitle="Collections, refunds and transaction history." list={api.payments.transactions} columns={[{ key: 'id', label: '#' }, { key: 'customer_name', label: 'Customer' }, { key: 'total_amount', label: 'Amount' }, { key: 'cash_amount', label: 'Cash' }, { key: 'transfer_amount', label: 'Bank / transfer' }, { key: 'created_at', label: 'Date' }]} />;
}

export function InventoryPage() {
  return <RecordsPage eyebrow="OPERATIONS" title="Inventory" subtitle="Live stock, movement history and warehouse locations." list={api.inventory.stock} columns={[{ key: 'id', label: '#' }, { key: 'product_name', label: 'Product' }, { key: 'location_name', label: 'Location' }, { key: 'quantity', label: 'Quantity' }, { key: 'updated_at', label: 'Updated' }]} />;
}
