import type { ReactNode } from 'react';
import { Center, Stack, Text } from '@mantine/core';

import type { UserProfile } from '../lib/api';

export function can(user: UserProfile, permission?: string) {
  if (!permission || user.is_superuser) return true;
  return user.permissions.includes(permission);
}

export function PermissionGuard({
  user,
  permission,
  children,
}: {
  user: UserProfile;
  permission?: string;
  children: ReactNode;
}) {
  if (can(user, permission)) return <>{children}</>;

  return (
    <Center mih="50vh">
      <Stack gap={4} align="center">
        <Text fw={800} size="lg">Permission required</Text>
        <Text c="dimmed" size="sm">Your account is not allowed to access this area.</Text>
      </Stack>
    </Center>
  );
}
