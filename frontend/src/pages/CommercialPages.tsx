import { CrudPage } from '../components/CrudPage';
import { api } from '../lib/api';

export function CouponsPage() {
  return (
    <CrudPage
      title="Coupons"
      subtitle="Discount rules available to sales invoices."
      list={api.coupons.list}
      create={api.coupons.create}
      update={api.coupons.update}
      remove={api.coupons.delete}
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

export function CartonPricingPage() {
  return (
    <CrudPage
      title="Carton pricing"
      subtitle="Pack sizes and carton prices for the product catalog."
      list={api.products.cartonPricings}
      create={api.products.createCartonPricing}
      update={api.products.updateCartonPricing}
      remove={api.products.deleteCartonPricing}
      fields={[{ key: 'product', label: 'Product ID', type: 'number', required: true }, { key: 'name', label: 'Label', required: true }, { key: 'units_per_carton', label: 'Units per carton', type: 'number', required: true }, { key: 'carton_price', label: 'Carton price', type: 'number', required: true }]}
      columns={[{ key: 'product_name', label: 'Product' }, { key: 'name', label: 'Pack' }, { key: 'units_per_carton', label: 'Units' }, { key: 'carton_price', label: 'Price' }]}
    />
  );
}
