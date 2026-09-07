import type { FormEvent } from 'react';
import { useEffect, useState } from 'react';
import { Button, Card, Group, Loader, SimpleGrid, Stack, Text, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';

import { CrudPage } from '../components/CrudPage';
import { api } from '../lib/api';

export function CompanyPage() {
  const [company, setCompany] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({ name: '', legal_name: '', registration_number: '', tax_number: '', email: '', phone: '', website: '' });

  async function load() {
    try {
      const data = await api.organization.company() as Record<string, unknown>;
      setCompany(data);
      setForm({ name: String(data.name || ''), legal_name: String(data.legal_name || ''), registration_number: String(data.registration_number || ''), tax_number: String(data.tax_number || ''), email: String(data.email || ''), phone: String(data.phone || ''), website: String(data.website || '') });
    } catch (error) {
      notifications.show({ title: 'Company unavailable', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const data = await api.organization.updateCompany(form) as Record<string, unknown>;
      setCompany(data);
      notifications.show({ title: 'Saved', message: 'Company details updated.', color: 'teal' });
    } catch (error) {
      notifications.show({ title: 'Save failed', message: error instanceof Error ? error.message : 'Request failed.', color: 'red' });
    } finally { setSaving(false); }
  }

  if (loading) return <Card className="glass" radius="lg" p={60} withBorder><Group justify="center"><Loader /></Group></Card>;

  return (
    <Stack gap="xl">
      <div><Text size="sm" c="indigo.3" fw={800}>ORGANIZATION</Text><Title order={1} mt={4}>Company profile</Title><Text c="dimmed" mt={4}>The single company context used by the ERP and accounting layer.</Text></div>
      <Card className="glass bento-card" withBorder radius="lg" p="xl" maw={900}>
        <form onSubmit={save}>
          <SimpleGrid cols={{ base: 1, md: 2 }}>
            {Object.keys(form).map((key) => <TextInput key={key} label={key.replaceAll('_', ' ')} value={form[key]} onChange={(event) => setForm((current) => ({ ...current, [key]: event.currentTarget.value }))} required={key === 'name'} />)}
          </SimpleGrid>
          <Group justify="space-between" mt="xl"><Text size="xs" c="dimmed">Company ID: {String(company?.id || '—')}</Text><Button type="submit" loading={saving}>Save company</Button></Group>
        </form>
      </Card>
    </Stack>
  );
}

export function SitesPage() {
  return (
    <CrudPage
      title="Sites"
      subtitle="Branches, warehouses and other organization locations."
      list={api.organization.sites}
      create={api.organization.createSite}
      update={api.organization.updateSite}
      remove={api.organization.deleteSite}
      fields={[{ key: 'code', label: 'Code', required: true }, { key: 'name', label: 'Name', required: true }, { key: 'site_type', label: 'Site type', required: true }, { key: 'parent', label: 'Parent site ID', type: 'number' }, { key: 'address_line_1', label: 'Address' }, { key: 'city', label: 'City' }, { key: 'country_code', label: 'Country code' }, { key: 'email', label: 'Email' }, { key: 'phone', label: 'Phone' }, { key: 'is_active', label: 'Active', type: 'boolean' }]}
      columns={[{ key: 'code', label: 'Code' }, { key: 'name', label: 'Site' }, { key: 'site_type', label: 'Type' }, { key: 'parent_name', label: 'Parent' }, { key: 'city', label: 'City' }, { key: 'is_active', label: 'Status' }]}
    />
  );
}

export function DepartmentsPage() {
  return (
    <CrudPage
      title="Departments"
      subtitle="Organizational departments and reporting structure."
      list={api.organization.departments}
      create={api.organization.createDepartment}
      update={api.organization.updateDepartment}
      remove={api.organization.deleteDepartment}
      fields={[{ key: 'code', label: 'Code', required: true }, { key: 'name', label: 'Name', required: true }, { key: 'site', label: 'Site ID', type: 'number' }, { key: 'description', label: 'Description' }, { key: 'is_active', label: 'Active', type: 'boolean' }]}
      columns={[{ key: 'code', label: 'Code' }, { key: 'name', label: 'Department' }, { key: 'site_name', label: 'Site' }, { key: 'description', label: 'Description' }, { key: 'is_active', label: 'Status' }]}
    />
  );
}
