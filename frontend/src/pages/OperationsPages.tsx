import { Badge, Button } from '@mantine/core';

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
  return <div style={{ display: 'grid', gap: 16 }}><div><b>Customer:</b> {String(data.customer_name || '—')}</div><div><b>Status:</b> {String(data.status || '—')}</div><div><b>Subtotal:</b> {money(data.subtotal)} &nbsp; <b>Total:</b> {money(data.total)}</div><div><b>Paid:</b> {money(data.net_paid_amount)} &nbsp; <b>Outstanding:</b> {money(data.outstanding_amount)}</div><div><b>Created:</b> {String(data.created_at || '—')}</div><div><b>Items</b><TableLike rows={items} fields={[['product_name', 'Product'], ['quantity', 'Qty'], ['unit_price', 'Unit price'], ['line_total', 'Total']]} moneyFields={['unit_price', 'line_total']} /></div></div>;
}

function purchaseDetails(data: Record<string, unknown>) {
  const items = Array.isArray(data.items) ? data.items as Record<string, unknown>[] : [];
  return <div style={{ display: 'grid', gap: 16 }}><div><b>Supplier:</b> {String(data.supplier_name || '—')}</div><div><b>Status:</b> {String(data.status || '—')}</div><div><b>Reference:</b> {String(data.reference || '—')}</div><div><b>Total:</b> {money(data.total_amount)} &nbsp; <b>Created:</b> {String(data.created_at || '—')}</div><div><b>Items</b><TableLike rows={items} fields={[['product_name', 'Product'], ['quantity', 'Qty'], ['unit_purchase_price', 'Unit cost'], ['total_amount', 'Total']]} moneyFields={['unit_purchase_price', 'total_amount']} /></div></div>;
}

function TableLike({ rows, fields, moneyFields }: { rows: Record<string, unknown>[]; fields: [string, string][]; moneyFields: string[] }) {
  return <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 8 }}><thead><tr>{fields.map(([, label]) => <th key={label} style={{ textAlign: 'left', padding: 8 }}>{label}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={String(row.id ?? index)}>{fields.map(([key]) => <td key={key} style={{ padding: 8 }}>{moneyFields.includes(key) ? money(row[key]) : String(row[key] ?? '—')}</td>)}</tr>)}</tbody></table></div>;
}

export function SalesPage() {
  return <RecordsPage eyebrow="COMMAND CENTER" title="Sales" subtitle="Invoice pipeline with draft-only confirmation and cancellation actions." list={api.invoices.list} details={{ load: api.invoices.get, render: invoiceDetails }} columns={[{ key: 'id', label: '#' }, { key: 'customer_name', label: 'Customer' }, { key: 'status', label: 'Status', format: statusBadge }, { key: 'total', label: 'Total' }, { key: 'paid_amount', label: 'Paid' }, { key: 'outstanding_amount', label: 'Outstanding' }, { key: 'created_at', label: 'Created' }]} actions={[{ label: 'Confirm', color: 'teal', visible: draftOnly, run: (row) => api.invoices.confirm(Number(row.id)) }, { label: 'Cancel', color: 'red', visible: draftOnly, run: (row) => api.invoices.cancel(Number(row.id)) }]} />;
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
