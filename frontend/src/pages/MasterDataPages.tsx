import { CrudPage } from '../components/CrudPage';
import { api } from '../lib/api';

export function ProductsPage() {
  return <CrudPage title="Products" subtitle="Catalog, pricing and live stock visibility." searchPlaceholder="Search products by name or category" list={api.products.list} create={api.products.create} update={api.products.update} remove={api.products.delete} fields={[{ key: 'name', label: 'Name', required: true }, { key: 'category', label: 'Category' }, { key: 'purchase_price', label: 'Purchase price', type: 'number', required: true }, { key: 'selling_price', label: 'Selling price', type: 'number', required: true }, { key: 'is_active', label: 'Active', type: 'boolean' }]} columns={[{ key: 'name', label: 'Product' }, { key: 'category', label: 'Category' }, { key: 'purchase_price', label: 'Buy price' }, { key: 'selling_price', label: 'Sell price' }, { key: 'stock_quantity', label: 'Stock' }, { key: 'sold_quantity', label: 'Sold' }, { key: 'is_active', label: 'Status' }]} />;
}

export function CustomersPage() {
  return <CrudPage title="Customers" subtitle="Manage the customer master and contact details." list={api.customers.list} create={api.customers.create} update={api.customers.update} remove={api.customers.delete} fields={[{ key: 'name', label: 'Name', required: true }, { key: 'phone', label: 'Phone' }, { key: 'address', label: 'Address' }]} columns={[{ key: 'name', label: 'Customer' }, { key: 'phone', label: 'Phone' }, { key: 'address', label: 'Address' }, { key: 'created_at', label: 'Created' }]} />;
}

export function SuppliersPage() {
  return <CrudPage title="Suppliers" subtitle="Supplier master data and purchasing contacts." list={api.suppliers.list} create={api.suppliers.create} update={api.suppliers.update} canDelete={false} fields={[{ key: 'name', label: 'Name', required: true }, { key: 'phone', label: 'Phone' }, { key: 'email', label: 'Email' }, { key: 'address', label: 'Address' }, { key: 'is_active', label: 'Active', type: 'boolean' }]} columns={[{ key: 'name', label: 'Supplier' }, { key: 'phone', label: 'Phone' }, { key: 'email', label: 'Email' }, { key: 'is_active', label: 'Status' }]} />;
}

export function EmployeesPage() {
  return (
    <CrudPage
      title="Employees"
      subtitle="Staff directory, reporting structure and organizational assignment."
      searchPlaceholder="Search by username, name or email"
      list={api.employees.list}
      create={api.employees.create}
      update={api.employees.update}
      remove={api.employees.delete}
      fields={[
        { key: 'user', label: 'User ID', type: 'number', required: true },
        { key: 'manager', label: 'Manager employee ID', type: 'number' },
        { key: 'work_site', label: 'Work site ID', type: 'number' },
        { key: 'department', label: 'Department ID', type: 'number' },
      ]}
      columns={[
        {
          key: 'user_details',
          label: 'Employee',
          render: (value) => {
            const user = value as Record<string, unknown> | null;
            if (!user) return '—';
            const name = [user.first_name, user.last_name].filter(Boolean).join(' ') || String(user.username || '—');
            return `${name} (@${user.username})`;
          },
        },
        {
          key: 'user_details',
          label: 'Email',
          render: (value) => String((value as Record<string, unknown> | null)?.email || '—'),
        },
        {
          key: 'manager_details',
          label: 'Manager',
          render: (value) => {
            const manager = value as Record<string, unknown> | null;
            if (!manager) return '—';
            return [manager.first_name, manager.last_name].filter(Boolean).join(' ') || String(manager.username || '—');
          },
        },
        { key: 'work_site', label: 'Work site' },
        { key: 'department', label: 'Department' },
        {
          key: 'user_details',
          label: 'Status',
          render: (value) => Boolean((value as Record<string, unknown> | null)?.is_active) ? 'Active' : 'Inactive',
        },
      ]}
    />
  );
}
