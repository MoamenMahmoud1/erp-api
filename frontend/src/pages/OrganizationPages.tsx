import type { FormEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { Button, Card, Group, Loader, SimpleGrid, Stack, Text, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';

import { CrudPage, type CrudOption } from '../components/CrudPage';
import { api, type Paginated } from '../lib/api';

const siteTypeOptions: CrudOption[] = [
  { value: 'head_office', label: 'Head office' },
  { value: 'branch', label: 'Branch' },
  { value: 'store', label: 'Store' },
];

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

type SiteOptions = { sites: Paginated };

function useSiteOptions() {
  const [data, setData] = useState<SiteOptions | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.organization.sites('?page_size=50')
      .then((sites) => setData({ sites }))
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : 'Unable to load site options.'));
  }, []);

  return { data, error };
}

export function SitesPage() {
  const { data, error } = useSiteOptions();
  const options = useMemo<CrudOption[]>(() => (data?.sites.results || []).map((site) => ({
    value: String(site.id),
    label: `${site.name || 'Unnamed site'}${site.code ? ` · ${site.code}` : ''}${site.site_type ? ` · ${String(site.site_type).replaceAll('_', ' ')}` : ''}`,
  })), [data]);

  if (error) return <Card className="glass" radius="xl" p="xl" withBorder><Text fw={800}>Sites unavailable</Text><Text c="dimmed" mt="xs">{error}</Text></Card>;
  if (!data) return <Card className="glass" radius="xl" p={56} withBorder><CenterLoader label="Loading site options…" /></Card>;

  return (
    <CrudPage
      title="Sites"
      subtitle="Branches, stores and other organization locations."
      list={api.organization.sites}
      create={api.organization.createSite}
      update={api.organization.updateSite}
      remove={api.organization.deleteSite}
      fields={[
        { key: 'code', label: 'Code', required: true },
        { key: 'name', label: 'Name', required: true },
        { key: 'site_type', label: 'Site type', type: 'select', options: siteTypeOptions, required: true },
        { key: 'parent', label: 'Parent site', type: 'select', options, clearable: true },
        { key: 'address_line_1', label: 'Address' },
        { key: 'city', label: 'City' },
        { key: 'country_code', label: 'Country code' },
        { key: 'email', label: 'Email' },
        { key: 'phone', label: 'Phone' },
        { key: 'is_active', label: 'Active', type: 'boolean' },
      ]}
      columns={[{ key: 'code', label: 'Code' }, { key: 'name', label: 'Site' }, { key: 'site_type', label: 'Type' }, { key: 'parent_name', label: 'Parent' }, { key: 'city', label: 'City' }, { key: 'is_active', label: 'Status' }]}
    />
  );
}

export function DepartmentsPage() {
  const { data, error } = useSiteOptions();
  const options = useMemo<CrudOption[]>(() => (data?.sites.results || []).map((site) => ({
    value: String(site.id),
    label: `${site.name || 'Unnamed site'}${site.code ? ` · ${site.code}` : ''}${site.site_type ? ` · ${String(site.site_type).replaceAll('_', ' ')}` : ''}`,
  })), [data]);

  if (error) return <Card className="glass" radius="xl" p="xl" withBorder><Text fw={800}>Departments unavailable</Text><Text c="dimmed" mt="xs">{error}</Text></Card>;
  if (!data) return <Card className="glass" radius="xl" p={56} withBorder><CenterLoader label="Loading department options…" /></Card>;

  return (
    <CrudPage
      title="Departments"
      subtitle="Organizational departments and reporting structure."
      list={api.organization.departments}
      create={api.organization.createDepartment}
      update={api.organization.updateDepartment}
      remove={api.organization.deleteDepartment}
      fields={[
        { key: 'code', label: 'Code', required: true },
        { key: 'name', label: 'Name', required: true },
        { key: 'site', label: 'Site', type: 'select', options, clearable: true },
        { key: 'description', label: 'Description' },
        { key: 'is_active', label: 'Active', type: 'boolean' },
      ]}
      columns={[{ key: 'code', label: 'Code' }, { key: 'name', label: 'Department' }, { key: 'site_name', label: 'Site' }, { key: 'description', label: 'Description' }, { key: 'is_active', label: 'Status' }]}
    />
  );
}

function CenterLoader({ label }: { label: string }) {
  return <><Group justify="center"><Loader size="sm" /></Group><Text ta="center" size="sm" c="dimmed" mt="md">{label}</Text></>;
}
