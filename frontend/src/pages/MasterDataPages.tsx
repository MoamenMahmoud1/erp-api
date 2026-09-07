import { CrudPage } from '../components/CrudPage';
import { api } from '../lib/api';

export function ProductsPage() {
  return (
    <CrudPage
      title="Products"
      subtitle="Catalog, pricing and live stock visibility."
      searchPlaceholder="Search products by name or category"
      list={api.products.list}
      create={api.products.create}
      update={api.products.update}
      remove={api.products.delete}
      fields={[
        { key: 'name', label: 'Name', required: true },
        { key: 'category', label: 'Category' },
        { key: 'purchase_price', label: 'Purchase price', type: 'number', required: true },
        { key: 'selling_price', label: 'Selling price', type: 'number', required: true },
        { key: 'is_active', label: 'Active', type: 'boolean' },
      ]}
      columns={[
        { key: 'name', label: 'Product' },
        { key: 'category', label: 'Category' },
        { key: 'purchase_price', label: 'Buy price' },
        { key: 'selling_price', label: 'Sell price' },
        { key: 'stock_quantity', label: 'Stock' },
        { key: 'sold_quantity', label: 'Sold' },
        { key: 'is_active', label: 'Status' },
      ]}
    />
  );
}

export function CustomersPage() {
  return (
    <CrudPage
      title="Customers"
      subtitle="Manage the customer master and contact details."
      list={api.customers.list}
      create={api.customers.create}
      update={api.customers.update}
      remove={api.customers.delete}
      fields={[
        { key: 'name', label: 'Name', required: true },
        { key: 'phone', label: 'Phone' },
        { key: 'address', label: 'Address' },
      ]}
      columns={[{ key: 'name', label: 'Customer' }, { key: 'phone', label: 'Phone' }, { key: 'address', label: 'Address' }, { key: 'created_at', label: 'Created' }]}
    />
  );
}

export function SuppliersPage() {
  return (
    <CrudPage
      title="Suppliers"
      subtitle="Supplier master data and purchasing contacts."
      list={api.suppliers.list}
      create={api.suppliers.create}
      update={api.suppliers.update}
      remove={async () => undefined}
      fields={[
        { key: 'name', label: 'Name', required: true },
        { key: 'phone', label: 'Phone' },
        { key: 'email', label: 'Email' },
        { key: 'address', label: 'Address' },
        { key: 'is_active', label: 'Active', type: 'boolean' },
      ]}
      columns={[{ key: 'name', label: 'Supplier' }, { key: 'phone', label: 'Phone' }, { key: 'email', label: 'Email' }, { key: 'is_active', label: 'Status' }]}
    />
  );
}
