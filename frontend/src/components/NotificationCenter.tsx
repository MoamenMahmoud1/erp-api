import { useCallback, useEffect, useState } from 'react';
import {
  ActionIcon,
  Badge,
  Button,
  Divider,
  Group,
  Indicator,
  Loader,
  Popover,
  ScrollArea,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core';
import { notifications as toastNotifications } from '@mantine/notifications';
import {
  IconBell,
  IconCheck,
  IconChevronRight,
  IconCircleCheck,
  IconClock,
  IconExternalLink,
  IconX,
} from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';

import { api, type NotificationItem } from '../lib/api';

type WebPushStatus = 'checking' | 'enabled' | 'available' | 'denied' | 'unsupported';

type NotificationCenterProps = {
  webPushStatus: WebPushStatus;
  webPushLoading: boolean;
  onEnableDesktopNotifications: () => void;
};

function getTargetPath(notification: NotificationItem) {
  if (!notification.target_id) return null;

  if (notification.target_type === 'invoice') return `/sales/${notification.target_id}`;
  if (notification.target_type === 'purchase') return `/purchases/${notification.target_id}`;
  if (['payment', 'payment_transaction', 'paymenttransaction'].includes(notification.target_type)) {
    return `/payments/${notification.target_id}`;
  }

  return null;
}

function formatTime(value: string) {
  const date = new Date(value);
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return 'Just now';

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  return days < 7 ? `${days}d ago` : date.toLocaleDateString();
}

function NotificationIcon({ type }: { type: string }) {
  if (type === 'approval_approved') return <IconCircleCheck size={16} />;
  if (type === 'approval_rejected') return <IconX size={16} />;
  return <IconClock size={16} />;
}

export function NotificationCenter({
  webPushStatus,
  webPushLoading,
  onEnableDesktopNotifications,
}: NotificationCenterProps) {
  const navigate = useNavigate();
  const [opened, setOpened] = useState(false);
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [recent, unread] = await Promise.all([
        api.notifications.list('?page_size=20'),
        api.notifications.list('?unread=true&page_size=1'),
      ]);
      setItems(recent.results as NotificationItem[]);
      setUnreadCount(unread.count);
    } catch {
      // Notifications are useful but must not block the ERP workspace.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const handlePush = (event: Event) => {
      const payload = (event as CustomEvent<{
        payload?: { notification?: { title?: string; body?: string } };
      }>).detail?.payload;
      const push = payload?.notification;
      if (!push) return;

      toastNotifications.show({
        title: push.title || 'ERP notification',
        message: push.body || '',
        autoClose: 6000,
      });
      void refresh();
    };

    window.addEventListener('erp-webpush-message', handlePush);
    return () => window.removeEventListener('erp-webpush-message', handlePush);
  }, [refresh]);

  const pushLabel =
    webPushStatus === 'enabled'
      ? 'Desktop push enabled'
      : webPushStatus === 'denied'
        ? 'Desktop push blocked'
        : webPushStatus === 'unsupported'
          ? 'Desktop push unavailable'
          : 'Enable desktop push';

  async function handleRead(notification: NotificationItem) {
    try {
      if (!notification.is_read) {
        await api.notifications.markRead(notification.id);
        setItems((current) => current.map((item) => (
          item.id === notification.id
            ? { ...item, is_read: true, read_at: new Date().toISOString() }
            : item
        )));
        setUnreadCount((count) => Math.max(0, count - 1));
      }

      const path = getTargetPath(notification);
      if (path) {
        setOpened(false);
        navigate(path);
      }
    } catch {
      toastNotifications.show({
        title: 'Unable to update notification',
        message: 'Please try again.',
        color: 'red',
      });
    }
  }

  async function handleReadAll() {
    if (!unreadCount) return;

    try {
      await api.notifications.markAllRead();
      setItems((current) => current.map((item) => ({
        ...item,
        is_read: true,
        read_at: item.read_at || new Date().toISOString(),
      })));
      setUnreadCount(0);
    } catch {
      toastNotifications.show({
        title: 'Unable to mark notifications as read',
        message: 'Please try again.',
        color: 'red',
      });
    }
  }

  return (
    <Popover
      opened={opened}
      onChange={setOpened}
      width={390}
      position="bottom-end"
      shadow="md"
      withinPortal
    >
      <Popover.Target>
        <Tooltip label={unreadCount ? `${unreadCount} unread` : 'Notifications'}>
          <Indicator
            disabled={!unreadCount}
            label={unreadCount > 99 ? '99+' : unreadCount}
            size={18}
            offset={4}
          >
            <ActionIcon
              variant={unreadCount ? 'light' : 'subtle'}
              radius="sm"
              size="lg"
              aria-label="Notifications"
              onClick={() => setOpened((value) => !value)}
            >
              <IconBell size={18} />
            </ActionIcon>
          </Indicator>
        </Tooltip>
      </Popover.Target>

      <Popover.Dropdown p={0}>
        <Stack gap={0}>
          <Group justify="space-between" px="md" py="sm">
            <div>
              <Text fw={800}>Notifications</Text>
              <Text size="xs" c="dimmed">
                {unreadCount ? `${unreadCount} unread` : 'All caught up'}
              </Text>
            </div>
            {unreadCount > 0 && (
              <Button variant="subtle" size="compact-xs" onClick={() => void handleReadAll()}>
                Mark all read
              </Button>
            )}
          </Group>

          <Divider />

          <ScrollArea h={360} offsetScrollbars>
            {loading ? (
              <Group justify="center" py="xl"><Loader size="sm" /></Group>
            ) : items.length === 0 ? (
              <Stack align="center" gap={6} py={48} px="md">
                <IconCheck size={24} />
                <Text fw={700}>No notifications</Text>
                <Text size="sm" c="dimmed" ta="center">
                  Important workspace events will appear here.
                </Text>
              </Stack>
            ) : (
              <Stack gap={0}>
                {items.map((notification) => {
                  const path = getTargetPath(notification);
                  return (
                    <button
                      key={notification.id}
                      type="button"
                      onClick={() => void handleRead(notification)}
                      style={{
                        width: '100%',
                        border: 0,
                        borderBottom: '1px solid var(--erp-border)',
                        background: notification.is_read ? 'transparent' : 'var(--mantine-color-default-hover)',
                        color: 'inherit',
                        textAlign: 'left',
                        cursor: 'pointer',
                        padding: '12px 14px',
                      }}
                    >
                      <Group align="flex-start" gap="sm" wrap="nowrap">
                        <Badge size="lg" variant="light" radius="sm" p={0} w={32} h={32}>
                          <NotificationIcon type={notification.notification_type} />
                        </Badge>

                        <Stack gap={3} style={{ flex: 1, minWidth: 0 }}>
                          <Group gap="xs" justify="space-between" wrap="nowrap">
                            <Text size="sm" fw={notification.is_read ? 650 : 800} lineClamp={1}>
                              {notification.title}
                            </Text>
                            <Text size="xs" c="dimmed" style={{ flexShrink: 0 }}>
                              {formatTime(notification.created_at)}
                            </Text>
                          </Group>
                          <Text size="sm" c="dimmed" lineClamp={2}>
                            {notification.body}
                          </Text>
                          {path && (
                            <Group gap={2}>
                              <Text size="xs" fw={700} c="blue">Open record</Text>
                              <IconChevronRight size={13} />
                            </Group>
                          )}
                        </Stack>
                      </Group>
                    </button>
                  );
                })}
              </Stack>
            )}
          </ScrollArea>

          <Divider />

          <Group justify="space-between" px="md" py="xs">
            <Text size="xs" c="dimmed">Recent notifications</Text>
            <Group gap={4}>
              <Button variant="subtle" size="compact-xs" onClick={() => void refresh()} loading={loading}>
                Refresh
              </Button>
              <Tooltip label={pushLabel}>
                <ActionIcon
                  variant={webPushStatus === 'enabled' ? 'light' : 'subtle'}
                  size="md"
                  radius="sm"
                  onClick={onEnableDesktopNotifications}
                  loading={webPushLoading || webPushStatus === 'checking'}
                  disabled={webPushStatus === 'denied' || webPushStatus === 'unsupported'}
                  aria-label="Enable desktop notifications"
                >
                  <IconExternalLink size={15} />
                </ActionIcon>
              </Tooltip>
            </Group>
          </Group>
        </Stack>
      </Popover.Dropdown>
    </Popover>
  );
}
