import { useEffect, useMemo, useState } from 'react';
import { Card, Center, Loader, Text } from '@mantine/core';

import { CrudPage, type CrudOption } from '../components/CrudPage';
import { can } from '../components/PermissionGuard';
import type { UserProfile } from '../lib/api';
import { api, type Paginated } from '../lib/api';

export function CouponsPage({ user }: { user: UserProfile }) {
  return (
    <CrudPage
      title="Coupons"
      subtitle="Discount rules available to sales invoices."
      filters={[
        { key: 'is_active', label: 'Status', type: 'select', options: [{ value: 'true', label: 'Active' }, { value: 'false', label: 'Inactive' }] },
        { key: 'discount_type', label: 'Discount type', type: 'select', options: [{ value: 'fixed', label: 'Fixed amount' }, { value: 'percentage', label: 'Percentage' }] },
      ]}
      list={api.coupons.list}
      create={can(user, 'coupons.add_coupon') ? api.coupons.create : undefined}
      update={api.coupons.update}
      remove={api.coupons.delete}
      canEdit={can(user, 'coupons.change_coupon')}
      canDelete={can(user, 'coupons.delete_coupon')}
      fields={[
        { key: 'code', label: 'Code', required: true },
        { key: 'discount_type', label: 'Discount type', type: 'select', options: [{ value: 'fixed', label: 'Fixed amount' }, { value: 'percentage', label: 'Percentage' }], required: true },
        { key: 'discount_value', label: 'Discount value', type: 'number', required: true },
        { key: 'minimum_invoice_amount', label: 'Minimum invoice amount', type: 'number' },
        { key: 'valid_from', label: 'Valid from' },
        { key: 'valid_until', label: 'Valid until' },
        { key: 'is_active', label: 'Active', type: 'boolean' },
      ]}
      columns={[
        { key: 'code', label: 'Code' },
        { key: 'discount_type', label: 'Type' },
        { key: 'discount_value', label: 'Value' },
        { key: 'minimum_invoice_amount', label: 'Min. invoice' },
        { key: 'valid_from', label: 'From' },
        { key: 'valid_until', label: 'Until' },
        { key: 'is_active', label: 'Status' },
      ]}
    />
  );
}

type ProductOptions = { products: Paginated };

export function CartonPricingPage({ user }: { user: UserProfile }) {
  const [data, setData] = useState<ProductOptions | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.products.list('?is_active=true&page_size=50')
      .then((products) => setData({ products }))
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : 'Unable to load products.'));
  }, []);

  const productOptions = useMemo<CrudOption[]>(() => (data?.products.results || []).map((product) => ({
    value: String(product.id),
    label: `${product.name || 'Unnamed product'}${product.category ? ` · ${product.category}` : ''}`,
  })), [data]);

  if (error) return <Card className="glass" radius="xl" p="xl" withBorder><Text fw={800}>Carton pricing unavailable</Text><Text c="dimmed" mt="xs">{error}</Text></Card>;
  if (!data) return <Card className="glass" radius="xl" p={56} withBorder><Center><Loader size="sm" /></Center><Text ta="center" size="sm" c="dimmed" mt="md">Loading products…</Text></Card>;

  return (
    <CrudPage
      title="Carton pricing"
      subtitle="Pack sizes and carton prices for the product catalog."
      filters={[{ key: 'product', label: 'Product', type: 'select', options: productOptions }]}
      list={api.products.cartonPricings}
      create={can(user, 'products.add_cartonpricing') ? api.products.createCartonPricing : undefined}
      update={api.products.updateCartonPricing}
      remove={api.products.deleteCartonPricing}
      canEdit={can(user, 'products.change_cartonpricing')}
      canDelete={can(user, 'products.delete_cartonpricing')}
      fields={[
        { key: 'product', label: 'Product', type: 'select', options: productOptions, required: true },
        { key: 'name', label: 'Label', required: true },
        { key: 'units_per_carton', label: 'Units per carton', type: 'number', required: true },
        { key: 'carton_price', label: 'Carton price', type: 'number', required: true },
      ]}
      columns={[{ key: 'product_name', label: 'Product' }, { key: 'name', label: 'Pack' }, { key: 'units_per_carton', label: 'Units' }, { key: 'carton_price', label: 'Price' }]}
    />
  );
}
