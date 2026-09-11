import { useEffect, useMemo, useState } from 'react';
import { Badge, Card, Center, Loader, Stack, Text } from '@mantine/core';

import { CrudPage, type CrudOption } from '../components/CrudPage';
import { api, type Paginated } from '../lib/api';

export function ProductsPage() {
  return <CrudPage title="Products" subtitle="Catalog, pricing and live stock visibility." searchPlaceholder="Search products by name or category" list={api.products.list} create={api.products.create} update={api.products.update} remove={api.products.delete} fields={[{ key: 'name', label: 'Name', required: true }, { key: 'category', label: 'Category' }, { key: 'purchase_price', label: 'Purchase price', type: 'number', required: true }, { key: 'selling_price', label: 'Selling price', type: 'number', required: true }, { key: 'is_active', label: 'Active', type: 'boolean' }]} columns={[{ key: 'name', label: 'Product' }, { key: 'category', label: 'Category' }, { key: 'purchase_price', label: 'Buy price' }, { key: 'selling_price', label: 'Sell price' }, { key: 'stock_quantity', label: 'Stock' }, { key: 'sold_quantity', label: 'Sold' }, { key: 'is_active', label: 'Status' }]} />;
}

export function CustomersPage() {
  return <CrudPage title="Customers" subtitle="Manage the customer master and contact details." list={api.customers.list} create={api.customers.create} update={api.customers.update} remove={api.customers.delete} fields={[{ key: 'name', label: 'Name', required: true }, { key: 'phone', label: 'Phone' }, { key: 'address', label: 'Address' }]} columns={[{ key: 'name', label: 'Customer' }, { key: 'phone', label: 'Phone' }, { key: 'address', label: 'Address' }, { key: 'created_at', label: 'Created' }]} />;
}

export function SuppliersPage() {
  return <CrudPage title="Suppliers" subtitle="Supplier master data and purchasing contacts." list={api.suppliers.list} create={api.suppliers.create} update={api.suppliers.update} canDelete={false} fields={[{ key: 'name', label: 'Name', required: true }, { key: 'phone', label: 'Phone' }, { key: 'email', label: 'Email' }, { key: 'address', label: 'Address' }, { key: 'is_active', label: 'Active', type: 'boolean' }]} columns={[{ key: 'name', label: 'Supplier' }, { key: 'phone', label: 'Phone' }, { key: 'email', label: 'Email' }, { key: 'is_active', label: 'Status' }]} />;
}

type EmployeePageOptions = {
  users: Paginated;
  employees: Paginated;
  sites: Paginated;
  departments: Paginated;
  roles: Paginated;
};

function EmployeePageLoading() {
  return (
    <Card className="glass" radius="xl" p={56} withBorder>
      <Center><Loader size="sm" /></Center>
      <Text ta="center" size="sm" c="dimmed" mt="md">Loading employee assignments…</Text>
    </Card>
  );
}

export function EmployeesPage() {
  const [options, setOptions] = useState<EmployeePageOptions | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.employees.options('?page_size=50'),
      api.employees.list('?page_size=50'),
      api.organization.sites('?page_size=50'),
      api.organization.departments('?page_size=50'),
      api.roles.list('?page_size=100'),
    ])
      .then(([users, employees, sites, departments, roles]) => {
        if (!active) return;
        setOptions({ users, employees, sites, departments, roles });
      })
      .catch((requestError) => {
        if (!active) return;
        setError(requestError instanceof Error ? requestError.message : 'Unable to load employee assignment options.');
      });

    return () => { active = false; };
  }, []);

  const userOptions = useMemo<CrudOption[]>(() => {
    if (!options) return [];
    return options.users.results.map((user) => {
      const name = [user.first_name, user.last_name].filter(Boolean).join(' ') || String(user.username || 'Unnamed user');
      const meta = [user.username ? `@${user.username}` : '', user.email ? String(user.email) : ''].filter(Boolean).join(' · ');
      return { value: String(user.id), label: meta ? `${name} · ${meta}` : name };
    });
  }, [options]);

  const managerOptions = useMemo<CrudOption[]>(() => {
    if (!options) return [];
    return options.employees.results.map((employee) => {
      const user = employee.user_details as Record<string, unknown> | null;
      const name = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || String(user?.username || `Employee #${employee.id}`);
      const meta = user?.username ? `@${user.username}` : '';
      return { value: String(employee.id), label: meta ? `${name} · ${meta}` : name };
    });
  }, [options]);

  const siteOptions = useMemo<CrudOption[]>(() => {
    if (!options) return [];
    return options.sites.results.map((site) => ({
      value: String(site.id),
      label: `${site.name || 'Unnamed site'}${site.code ? ` · ${site.code}` : ''}${site.site_type ? ` · ${site.site_type}` : ''}`,
    }));
  }, [options]);

  const departmentOptions = useMemo<CrudOption[]>(() => {
    if (!options) return [];
    return options.departments.results.map((department) => ({
      value: String(department.id),
      label: `${department.name || 'Unnamed department'}${department.code ? ` · ${department.code}` : ''}${department.site_name ? ` · ${department.site_name}` : ''}`,
    }));
  }, [options]);

  const roleOptions = useMemo<CrudOption[]>(() => {
    if (!options) return [];
    return options.roles.results.map((role) => ({
      value: String(role.id),
      label: String(role.name || `Role #${role.id}`),
    }));
  }, [options]);

  if (error) {
    return (
      <Card className="glass" radius="xl" p="xl" withBorder>
        <Text fw={800}>Employees unavailable</Text>
        <Text c="dimmed" mt="xs">{error}</Text>
      </Card>
    );
  }

  if (!options) return <EmployeePageLoading />;

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
        { key: 'user', label: 'User', type: 'select', options: userOptions, required: true, createOnly: true },
        {
          key: 'role_id',
          label: 'Role',
          type: 'select',
          options: roleOptions,
          clearable: true,
          editValue: (row) => {
            const role = row.role as Record<string, unknown> | null;
            const userRole = (row.user_details as Record<string, unknown> | null)?.role as Record<string, unknown> | null;
            return role?.id ?? userRole?.id ?? '';
          },
        },
        { key: 'manager', label: 'Manager', type: 'select', options: managerOptions, clearable: true },
        { key: 'work_site', label: 'Work site', type: 'select', options: siteOptions, clearable: true },
        { key: 'department', label: 'Department', type: 'select', options: departmentOptions, clearable: true },
      ]}
      columns={[
        {
          key: 'employee',
          label: 'Employee',
          render: (_value, row) => {
            const user = row.user_details as Record<string, unknown> | null;
            if (!user) return '—';
            const name = [user.first_name, user.last_name].filter(Boolean).join(' ') || String(user.username || '—');
            const role = user.role as Record<string, unknown> | null;
            const roleName = String(role?.name || '');
            return (
              <Stack gap={2}>
                <Text size="sm" fw={600}>{name}</Text>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Text size="xs" c="dimmed">@{String(user.username || '—')}</Text>
                  {roleName && <Badge size="xs" variant="light" color="erp">{roleName}</Badge>}
                </div>
              </Stack>
            );
          },
        },
        {
          key: 'email',
          label: 'Email',
          render: (_value, row) => String((row.user_details as Record<string, unknown> | null)?.email || '—'),
        },
        {
          key: 'manager_name',
          label: 'Manager',
          render: (_value, row) => {
            const manager = row.manager_details as Record<string, unknown> | null;
            if (!manager) return '—';
            return [manager.first_name, manager.last_name].filter(Boolean).join(' ') || String(manager.username || '—');
          },
        },
        { key: 'work_site_name', label: 'Work site' },
        { key: 'department_name', label: 'Department' },
        {
          key: 'status',
          label: 'Status',
          render: (_value, row) => Boolean((row.user_details as Record<string, unknown> | null)?.is_active) ? 'Active' : 'Inactive',
        },
      ]}
    />
  );
}
