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
    <main className="login-page login-page-modern">
      <style>{`
        .login-page-modern .login-frame {
          width: min(1040px, 100%);
          grid-template-columns: minmax(0, 1.08fr) minmax(380px, 0.92fr);
          border-radius: 22px;
          box-shadow: 0 22px 48px rgba(0, 0, 0, 0.28);
        }
        .login-page-modern .login-brand-panel {
          position: relative;
          min-height: 600px;
          padding: 50px;
          overflow: hidden;
          background: var(--erp-surface-raised);
        }
        .login-page-modern .login-brand-panel::before {
          content: '';
          position: absolute;
          top: 50px;
          left: 0;
          width: 3px;
          height: 112px;
          border-radius: 0 3px 3px 0;
          background: var(--erp-primary);
        }
        .login-page-modern .login-brand-mark {
          width: 50px;
          height: 50px;
          margin-bottom: 28px;
          border-radius: 13px;
          box-shadow: inset 0 -3px 0 var(--erp-primary);
        }
        .login-page-modern .login-brand-title {
          max-width: 500px;
          margin-top: 12px;
          font-size: clamp(2.35rem, 4.3vw, 3.35rem);
          line-height: 1.03;
          letter-spacing: -0.048em;
        }
        .login-page-modern .login-brand-copy {
          max-width: 490px;
          margin-top: 22px;
          font-size: 1rem;
          line-height: 1.65;
        }
        .login-page-modern .login-brand-footer {
          max-width: 430px;
          padding-top: 22px;
        }
        .login-page-modern .login-form-panel {
          min-height: 600px;
          padding: 50px;
        }
        .login-page-modern .login-form-intro {
          margin-bottom: 30px;
        }
        .login-page-modern .login-form-intro > :first-child {
          color: var(--erp-primary) !important;
          font-size: 0.78rem;
          letter-spacing: .1em;
          text-transform: uppercase;
        }
        .login-page-modern .login-form-intro h2 {
          font-size: clamp(1.9rem, 3.2vw, 2.35rem);
          letter-spacing: -0.035em;
        }
        .login-page-modern .login-form .mantine-TextInput-input,
        .login-page-modern .login-form .mantine-PasswordInput-input {
          min-height: 50px;
          border-radius: 10px;
          border-color: var(--erp-border-strong);
          background: var(--erp-surface-raised);
          transition: border-color 140ms ease, box-shadow 140ms ease, background 140ms ease;
        }
        .login-page-modern .login-form .mantine-TextInput-input:focus,
        .login-page-modern .login-form .mantine-PasswordInput-input:focus {
          border-color: var(--erp-primary);
          background: var(--erp-surface);
          box-shadow: var(--erp-focus);
        }
        .login-page-modern .login-form label {
          margin-bottom: 7px;
          font-weight: 700;
        }
        .login-page-modern .login-submit {
          min-height: 50px;
          margin-top: 4px;
          border-radius: 10px;
          font-weight: 800;
          box-shadow: var(--erp-shadow-xs);
        }
        .login-page-modern .login-submit:hover {
          box-shadow: var(--erp-shadow-sm);
        }
        .login-page-modern .login-form-note {
          margin-top: 24px;
          padding-top: 17px;
        }
        @media (max-width: 800px) {
          .login-page-modern .login-frame { grid-template-columns: 1fr; }
          .login-page-modern .login-brand-panel { min-height: auto; padding: 34px 30px; }
          .login-page-modern .login-brand-panel::before { top: 34px; height: 92px; }
          .login-page-modern .login-form-panel { min-height: auto; padding: 34px 30px; }
        }
        @media (max-width: 520px) {
          .login-page-modern .login-brand-panel,
          .login-page-modern .login-form-panel { padding: 26px 22px; }
          .login-page-modern .login-brand-title { font-size: 2rem; }
        }
      `}</style>

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
