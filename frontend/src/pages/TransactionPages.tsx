import type { FormEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { Button, Card, Divider, Group, NumberInput, Select, SimpleGrid, Stack, Text, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';

import { api, type Paginated } from '../lib/api';

type Line = { product: string; quantity: number | string; unit_purchase_price?: number | string };

function useOptions() {
  const [products, setProducts] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [customers, setCustomers] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });
  const [suppliers, setSuppliers] = useState<Paginated>({ count: 0, next: null, previous: null, results: [] });

  useEffect(() => {
    Promise.all([
      api.products.list('?page_size=50'),
      api.customers.list('?page_size=50'),
      api.suppliers.list('?page_size=50'),
    ]).then(([productData, customerData, supplierData]) => {
      setProducts(productData); setCustomers(customerData); setSuppliers(supplierData);
    }).catch((error) => notifications.show({ title: 'Unable to load form options', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }));
  }, []);

  return {
    productOptions: products.results.map((row) => ({ value: String(row.id), label: `${row.name || row.id} · stock ${row.stock_quantity ?? '—'}` })),
    customerOptions: customers.results.map((row) => ({ value: String(row.id), label: `${row.name || row.id}${row.phone ? ` · ${row.phone}` : ''}` })),
    supplierOptions: suppliers.results.map((row) => ({ value: String(row.id), label: `${row.name || row.id}${row.phone ? ` · ${row.phone}` : ''}` })),
  };
}

function WorkflowHeader({ eyebrow, title, subtitle }: { eyebrow: string; title: string; subtitle: string }) {
  return <div><Text size="sm" c="indigo.3" fw={800}>{eyebrow}</Text><Title order={1} mt={4}>{title}</Title><Text c="dimmed" mt={4}>{subtitle}</Text></div>;
}

export function CreateInvoicePage() {
  const { productOptions, customerOptions } = useOptions();
  const [customer, setCustomer] = useState('');
  const [lines, setLines] = useState<Line[]>([{ product: '', quantity: 1 }]);
  const [loading, setLoading] = useState(false);

  function updateLine(index: number, patch: Partial<Line>) { setLines((current) => current.map((line, lineIndex) => lineIndex === index ? { ...line, ...patch } : line)); }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!customer || lines.some((line) => !line.product || Number(line.quantity) < 1)) return;
    setLoading(true);
    try {
      await api.invoices.create({ customer: Number(customer), items: lines.map((line) => ({ product: Number(line.product), quantity: Number(line.quantity) })) });
      notifications.show({ title: 'Invoice created', message: 'The invoice is ready for confirmation.', color: 'teal' });
      setLines([{ product: '', quantity: 1 }]);
    } catch (error) { notifications.show({ title: 'Invoice failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
    finally { setLoading(false); }
  }

  return <Stack gap="xl"><WorkflowHeader eyebrow="SALES" title="New invoice" subtitle="Create a draft, then confirm it when the sale is ready." /><Card className="glass" withBorder radius="lg" p="xl" maw={980}><form onSubmit={submit}><Stack><Select label="Customer" searchable data={customerOptions} value={customer} onChange={(value) => setCustomer(value || '')} required /><Divider my="sm" /><Text fw={800}>Items</Text>{lines.map((line, index) => <SimpleGrid key={index} cols={{ base: 1, sm: 3 }}><Select label={`Product ${index + 1}`} searchable data={productOptions} value={line.product} onChange={(value) => updateLine(index, { product: value || '' })} required /><NumberInput label="Quantity" min={1} value={line.quantity} onChange={(value) => updateLine(index, { quantity: value })} required /><Group align="flex-end"><Button type="button" variant="subtle" color="red" disabled={lines.length === 1} onClick={() => setLines((current) => current.filter((_, lineIndex) => lineIndex !== index))}>Remove</Button></Group></SimpleGrid>)}<Button type="button" variant="light" onClick={() => setLines((current) => [...current, { product: '', quantity: 1 }])}>Add item</Button><Button type="submit" loading={loading} variant="gradient" gradient={{ from: 'indigo', to: 'cyan', deg: 120 }}>Create draft invoice</Button></Stack></form></Card></Stack>;
}

export function CreatePurchasePage() {
  const { productOptions, supplierOptions } = useOptions();
  const [supplier, setSupplier] = useState('');
  const [reference, setReference] = useState('');
  const [lines, setLines] = useState<Line[]>([{ product: '', quantity: 1, unit_purchase_price: '' }]);
  const [loading, setLoading] = useState(false);

  function updateLine(index: number, patch: Partial<Line>) { setLines((current) => current.map((line, lineIndex) => lineIndex === index ? { ...line, ...patch } : line)); }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!supplier || lines.some((line) => !line.product || Number(line.quantity) < 1 || line.unit_purchase_price === '' || Number(line.unit_purchase_price) < 0)) return;
    setLoading(true);
    try {
      await api.purchases.create({ supplier: Number(supplier), reference, items: lines.map((line) => ({ product: Number(line.product), quantity: Number(line.quantity), unit_purchase_price: Number(line.unit_purchase_price) })) });
      notifications.show({ title: 'Purchase created', message: 'The purchase is ready for confirmation.', color: 'teal' });
      setReference(''); setLines([{ product: '', quantity: 1, unit_purchase_price: '' }]);
    } catch (error) { notifications.show({ title: 'Purchase failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
    finally { setLoading(false); }
  }

  return <Stack gap="xl"><WorkflowHeader eyebrow="PURCHASING" title="New purchase" subtitle="Create a draft purchase with supplier cost snapshots." /><Card className="glass" withBorder radius="lg" p="xl" maw={980}><form onSubmit={submit}><Stack><Select label="Supplier" searchable data={supplierOptions} value={supplier} onChange={(value) => setSupplier(value || '')} required /><TextInput label="Reference" value={reference} onChange={(event) => setReference(event.currentTarget.value)} /><Divider my="sm" /><Text fw={800}>Items</Text>{lines.map((line, index) => <SimpleGrid key={index} cols={{ base: 1, sm: 3 }}><Select label={`Product ${index + 1}`} searchable data={productOptions} value={line.product} onChange={(value) => updateLine(index, { product: value || '' })} required /><NumberInput label="Quantity" min={1} value={line.quantity} onChange={(value) => updateLine(index, { quantity: value })} required /><NumberInput label="Unit purchase price" min={0} value={line.unit_purchase_price} onChange={(value) => updateLine(index, { unit_purchase_price: value })} required /></SimpleGrid>)}<Group><Button type="button" variant="light" onClick={() => setLines((current) => [...current, { product: '', quantity: 1, unit_purchase_price: '' }])}>Add item</Button><Button type="submit" loading={loading} variant="gradient" gradient={{ from: 'violet', to: 'indigo', deg: 120 }}>Create draft purchase</Button></Group></Stack></form></Card></Stack>;
}

export function CollectPaymentPage() {
  const { customerOptions } = useOptions();
  const [customer, setCustomer] = useState('');
  const [cash, setCash] = useState<number | string>(0);
  const [transfer, setTransfer] = useState<number | string>(0);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!customer || Number(cash) + Number(transfer) <= 0) return;
    setLoading(true);
    try {
      await api.payments.collections({ customer: Number(customer), cash_amount: Number(cash), transfer_amount: Number(transfer) });
      notifications.show({ title: 'Payment collected', message: 'The payment was allocated automatically.', color: 'teal' });
      setCash(0); setTransfer(0);
    } catch (error) { notifications.show({ title: 'Collection failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
    finally { setLoading(false); }
  }

  const total = useMemo(() => Number(cash || 0) + Number(transfer || 0), [cash, transfer]);
  return <Stack gap="xl"><WorkflowHeader eyebrow="PAYMENTS" title="Collect payment" subtitle="Collect cash or bank transfer against the customer's oldest open invoices." /><Card className="glass" withBorder radius="lg" p="xl" maw={760}><form onSubmit={submit}><Stack><Select label="Customer" searchable data={customerOptions} value={customer} onChange={(value) => setCustomer(value || '')} required /><SimpleGrid cols={{ base: 1, sm: 2 }}><NumberInput label="Cash" min={0} value={cash} onChange={setCash} /><NumberInput label="Bank / transfer" min={0} value={transfer} onChange={setTransfer} /></SimpleGrid><Text ta="right" size="xl" fw={900}>Total: {total.toFixed(2)}</Text><Button type="submit" loading={loading}>Collect payment</Button></Stack></form></Card></Stack>;
}

export function SupplierPaymentPage() {
  const { supplierOptions } = useOptions();
  const [supplier, setSupplier] = useState('');
  const [cash, setCash] = useState<number | string>(0);
  const [transfer, setTransfer] = useState<number | string>(0);
  const [reference, setReference] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!supplier || Number(cash) + Number(transfer) <= 0) return;
    setLoading(true);
    try {
      await api.purchases.supplierPayment({ supplier: Number(supplier), cash_amount: Number(cash), transfer_amount: Number(transfer), reference });
      notifications.show({ title: 'Supplier paid', message: 'The payment was allocated against open purchases.', color: 'teal' });
      setCash(0); setTransfer(0); setReference('');
    } catch (error) { notifications.show({ title: 'Supplier payment failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' }); }
    finally { setLoading(false); }
  }

  return <Stack gap="xl"><WorkflowHeader eyebrow="PAYMENTS" title="Pay supplier" subtitle="Settle supplier payables using cash or bank transfer." /><Card className="glass" withBorder radius="lg" p="xl" maw={760}><form onSubmit={submit}><Stack><Select label="Supplier" searchable data={supplierOptions} value={supplier} onChange={(value) => setSupplier(value || '')} required /><SimpleGrid cols={{ base: 1, sm: 2 }}><NumberInput label="Cash" min={0} value={cash} onChange={setCash} /><NumberInput label="Bank / transfer" min={0} value={transfer} onChange={setTransfer} /></SimpleGrid><TextInput label="Reference" value={reference} onChange={(event) => setReference(event.currentTarget.value)} /><Button type="submit" loading={loading}>Pay supplier</Button></Stack></form></Card></Stack>;
}
