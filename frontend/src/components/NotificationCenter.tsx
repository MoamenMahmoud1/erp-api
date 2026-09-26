import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActionIcon, Badge, Button, Divider, Group, Indicator, Loader, Popover, ScrollArea, Stack, Text, Tooltip } from '@mantine/core';
import { notifications as toastNotifications } from '@mantine/notifications';
import { IconBell, IconCheck, IconChevronRight, IconCircleCheck, IconClock, IconExternalLink, IconX } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';

import { api, type NotificationItem } from '../lib/api';

type WebPushStatus = 'checking' | 'enabled' | 'available' | 'denied' | 'unsupported';

type NotificationCenterProps = {
  webPushStatus: WebPushStatus;
  webPushLoading: boolean;
  onEnableDesktopNotifications: () => void;
};

function targetPath(notification: NotificationItem) {
  if (!notification.target_id) return null;

  switch (notification.target_type) {
    case 'invoice':
      return `/sales/${notification.target_id}`;
    case 'purchase':
      return `/purchases/${notification.target_id}`;
    case 'payment':
    case 'payment_transaction':
    case 'paymenttransaction':
      return `/payments/${notification.target_id}`;
    default:
      return null;
  }
}

function relativeTime(value: string) {
  const date = new Date(value);
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return 'Just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString();
}

function typeIcon(notification: NotificationItem) {
  if (notification.notification_type === 'approval_approved') {
    return <IconCircleCheck size={17} />;
  }
  if (notification.notification_type === 'approval_rejected') {
    return <IconX size={17} />;
  }
  return <IconClock size={17} />;
}

export function NotificationCenter({
  webPushStatus,
  webPushLoading,
  onEnableDesktopNotifications,
}: NotificationCenterProps) {
  const navigate = useNavigate();
  const [opened, setOpened] = useState(false);
  const [loading, setLoading] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [recent, unread] = await Promise.all([
        api.notifications.list('?page_size=20'),
        api.notifications.list('?unread=true&page_size=1'),
      ]);
      setNotifications(recent.results as NotificationItem[]);
      setUnreadCount(unread.count);
    } catch {
      // The notification center is non-critical to the main workspace.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const handleRefresh = () => { void refresh(); };
    window.addEventListener('erp-notifications-refresh', handleRefresh);
    return () => window.removeEventListener('erp-notifications-refresh', handleRefresh);
  }, [refresh]);

  useEffect(() => {
    const handlePushMessage = (event: Event) => {
      const detail = (event as CustomEvent<{
        payload?: { notification?: { title?: string; body?: string } };
      }>).detail;
      const push = detail?.payload?.notification;
      if (!push) return;

      toastNotifications.show({
        title: push.title || 'ERP notification',
        message: push.body || '',
        autoClose: 6000,
      });
      void refresh();
    };

    window.addEventListener('erp-webpush-message', handlePushMessage);
    return () => window.removeEventListener('erp-webpush-message', handlePushMessage);
  }, [refresh]);

  const desktopHint = useMemo(() => {
    if (webPushStatus === 'enabled') return 'Desktop push notifications enabled';
    if (webPushStatus === 'denied') return 'Notifications are blocked by the browser';
    if (webPushStatus === 'unsupported') return 'Desktop push is unavailable in this browser';
    return 'Enable desktop push notifications';
  }, [webPushStatus]);

  async function markRead(notification: NotificationItem) {
    if (!notification.is_read) {
      await api.notifications.markRead(notification.id);
      setNotifications((current) => current.map((item) => (
        item.id === notification.id
          ? { ...item, is_read: true, read_at: new Date().toISOString() }
          : item
      )));
      setUnreadCount((count) => Math.max(0, count - 1));
    }

    const path = targetPath(notification);
    if (path) {
      setOpened(false);
      navigate(path);
    }
  }

  async function markAllRead() {
    if (!unreadCount) return;
    await api.notifications.markAllRead();
    setNotifications((current) => current.map((item) => (
      item.is_read ? item : { ...item, is_read: true, read_at: new Date().toISOString() }
    )));
    setUnreadCount(0);
  }

  return (
    <Popover
      opened={opened}
      onChange={setOpened}
      width={390}
      position="bottom-end"
      shadow="md"
      withArrow
      withinPortal
    >
      <Popover.Target>
        <Tooltip label={unreadCount ? `${unreadCount} unread notification${unreadCount === 1 ? '' : 's'}` : 'Notifications'}>
          <Indicator
            disabled={unreadCount === 0}
            label={unreadCount > 99 ? '99+' : unreadCount}
            size={18}
            offset={4}
            processing={false}
          >
            <ActionIcon
              variant={unreadCount ? 'light' : 'subtle'}
              radius="sm"
              size="lg"
              onClick={() => setOpened((value) => !value)}
              aria-label="Notifications"
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
            <Group gap={4}>
              {unreadCount > 0 && (
                <Button
                  variant="subtle"
                  size="compact-xs"
                  onClick={() => { void markAllRead(); }}
                >
                  Mark all read
                </Button>
              )}
              <Tooltip label={desktopHint}>
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

          <Divider />

          <ScrollArea h={360} offsetScrollbars>
            {loading ? (
              <Group justify="center" py="xl">
                <Loader size="sm" />
              </Group>
            ) : notifications.length === 0 ? (
              <Stack align="center" justify="center" py={48} px="md" gap={6}>
                <IconCheck size={24} />
                <Text fw={700}>No notifications</Text>
                <Text size="sm" c="dimmed" ta="center">
                  Approval updates and other important workspace events will appear here.
                </Text>
              </Stack>
            ) : (
              <Stack gap={0}>
                {notifications.map((notification) => {
                  const path = targetPath(notification);
                  return (
                    <button
                      key={notification.id}
                      type="button"
                      onClick={() => { void markRead(notification); }}
                      style={{
                        appearance: 'none',
                        width: '100%',
                        border: 0,
                        borderBottom: '1px solid var(--erp-border)',
                        background: notification.is_read ? 'transparent' : 'var(--mantine-color-dark-7)',
                        color: 'inherit',
                        textAlign: 'left',
                        cursor: 'pointer',
                        padding: '12px 14px',
                      }}
                    >
                      <Group align="flex-start" gap="sm" wrap="nowrap">
                        <Indicator
                          disabled={notification.is_read}
                          color="red"
                          size={7}
                          offset={-1}
                        >
                          <Badge
                            size="lg"
                            variant="light"
                            radius="sm"
                            p={0}
                            w={32}
                            h={32}
                          >
                            {typeIcon(notification)}
                          </Badge>
                        </Indicator>

                        <Stack gap={3} style={{ flex: 1, minWidth: 0 }}>
                          <Group gap="xs" justify="space-between" wrap="nowrap">
                            <Text size="sm" fw={notification.is_read ? 650 : 800} lineClamp={1}>
                              {notification.title}
                            </Text>
                            <Text size="xs" c="dimmed" style={{ flexShrink: 0 }}>
                              {relativeTime(notification.created_at)}
                            </Text>
                          </Group>
                          <Text size="sm" c="dimmed" lineClamp={2}>
                            {notification.body}
                          </Text>
                          {path && (
                            <Group gap={3}>
                              <Text size="xs" fw={700} c="blue">
                                Open related record
                              </Text>
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
            <Button
              variant="subtle"
              size="compact-xs"
              onClick={() => { void refresh(); }}
              loading={loading}
            >
              Refresh
            </Button>
          </Group>
        </Stack>
      </Popover.Dropdown>
    </Popover>
  );
}
