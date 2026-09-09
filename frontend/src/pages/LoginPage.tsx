import type { FormEvent } from 'react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, PasswordInput, Stack, Text, TextInput, Title } from '@mantine/core';
import { IconArrowRight, IconShieldCheck } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';

import { api } from '../lib/api';

export function LoginPage() {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function submit(event: FormEvent<HTMLFormElement>) {
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
    <main className="login-page">
      <section className="login-frame" aria-label="ERP sign in">
        <div className="login-brand-panel">
          <div>
            <div className="login-brand-mark" aria-hidden="true">E</div>
            <Text className="login-eyebrow" size="xs" fw={800} tt="uppercase" lts=".12em">
              ERP Workspace
            </Text>
            <Title order={1} className="login-brand-title">
              Everything your operation needs, in one place.
            </Title>
            <Text className="login-brand-copy" mt="md">
              Sales, inventory and finance stay connected so the team can work from the same source of truth.
            </Text>
          </div>

          <div className="login-brand-footer">
            <span className="login-security-icon" aria-hidden="true"><IconShieldCheck size={16} /></span>
            <div>
              <Text size="sm" fw={700}>Role-based workspace</Text>
              <Text size="xs" c="dimmed" mt={2}>Your access is tailored to your responsibilities.</Text>
            </div>
          </div>
        </div>

        <div className="login-form-panel">
          <div className="login-form-intro">
            <Text size="sm" fw={700} c="dimmed">Sign in</Text>
            <Title order={2} mt={4}>Welcome back</Title>
            <Text size="sm" c="dimmed" mt={6} maw={420}>
              Continue to your ERP workspace.
            </Text>
          </div>

          <form onSubmit={submit} className="login-form">
            <Stack gap="lg">
              <TextInput
                label="Username or email"
                placeholder="you@example.com"
                value={identifier}
                onChange={(event) => setIdentifier(event.currentTarget.value)}
                autoComplete="username"
                required
                autoFocus
                size="md"
              />
              <PasswordInput
                label="Password"
                placeholder="Enter your password"
                value={password}
                onChange={(event) => setPassword(event.currentTarget.value)}
                autoComplete="current-password"
                required
                size="md"
              />
              <Button
                type="submit"
                size="md"
                loading={loading}
                fullWidth
                color="erp"
                rightSection={<IconArrowRight size={17} />}
                className="login-submit"
              >
                Sign in
              </Button>
            </Stack>
          </form>

          <Text className="login-form-note" size="xs" c="dimmed">
            Access is protected by your assigned ERP permissions.
          </Text>
        </div>
      </section>
    </main>
  );
}
