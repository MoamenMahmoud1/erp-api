import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Center, Container, PasswordInput, Stack, Text, TextInput, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';

import { api } from '../lib/api';

export function LoginPage() {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    try {
      await api.auth.login(identifier.trim(), password);
      navigate('/', { replace: true });
    } catch (error) {
      notifications.show({
        title: 'Login failed',
        message: error instanceof Error ? error.message : 'Please check your credentials.',
        color: 'red',
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-bg" style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 24 }}>
      <div className="aurora-orb one" />
      <div className="aurora-orb two" />
      <Container size={460} w="100%">
        <div className="glass bento-card" style={{ borderRadius: 28, padding: 34, boxShadow: '0 24px 80px rgba(0,0,0,.28)' }}>
          <Stack gap="xl">
            <div>
              <Text size="xs" tt="uppercase" fw={900} c="indigo.3" lts=".12em">ERP Command Center</Text>
              <Title order={1} mt={7} style={{ letterSpacing: '-0.04em' }}>Welcome back</Title>
              <Text c="dimmed" mt={6}>Sign in to manage sales, inventory and finance.</Text>
            </div>

            <form onSubmit={submit}>
              <Stack gap="md">
                <TextInput label="Username or email" placeholder="you@example.com" value={identifier} onChange={(event) => setIdentifier(event.currentTarget.value)} required autoFocus />
                <PasswordInput label="Password" placeholder="Your password" value={password} onChange={(event) => setPassword(event.currentTarget.value)} required />
                <Button type="submit" size="md" loading={loading} fullWidth variant="gradient" gradient={{ from: 'indigo', to: 'cyan', deg: 120 }}>
                  Sign in
                </Button>
              </Stack>
            </form>
          </Stack>
        </div>
      </Container>
    </div>
  );
}
