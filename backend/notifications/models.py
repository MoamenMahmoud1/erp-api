from django.conf import settings
from django.db import models
from django.utils import timezone


class PushDevice(models.Model):
    """A Firebase Installation registered for the current authenticated user."""

    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_devices",
    )
    installation_id = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=20, choices=Platform.choices)
    firebase_app_id = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-last_seen_at", "-id")
        indexes = [
            models.Index(fields=("user", "is_active", "last_seen_at"), name="push_device_user_active_idx"),
        ]

    def touch(self, *, platform: str, firebase_app_id: str = ""):
        self.platform = platform
        self.firebase_app_id = firebase_app_id
        self.is_active = True
        self.last_seen_at = timezone.now()
        self.last_error = ""
        self.save(
            update_fields=(
                "platform",
                "firebase_app_id",
                "is_active",
                "last_seen_at",
                "last_error",
                "updated_at",
            )
        )

    def deactivate(self, error: str = ""):
        self.is_active = False
        self.last_error = error[:2000]
        self.save(update_fields=("is_active", "last_error", "updated_at"))


class Notification(models.Model):
    """Durable in-app notification owned by a single authenticated user."""

    class NotificationType(models.TextChoices):
        APPROVAL_REQUESTED = "approval_requested", "Approval requested"
        APPROVAL_APPROVED = "approval_approved", "Approval approved"
        APPROVAL_REJECTED = "approval_rejected", "Approval rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.PositiveBigIntegerField(null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)
    dedupe_key = models.CharField(max_length=255, unique=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("user", "read_at", "created_at"), name="notif_user_read_created_idx"),
            models.Index(fields=("user", "created_at"), name="notif_user_created_idx"),
        ]

    @property
    def is_read(self):
        return self.read_at is not None

    def __str__(self):
        return f"{self.notification_type}: {self.title}"


class NotificationDelivery(models.Model):
    """Tracks push delivery independently for each notification/device pair."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="push_deliveries",
    )
    device = models.ForeignKey(
        PushDevice,
        on_delete=models.CASCADE,
        related_name="notification_deliveries",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("notification", "device"),
                name="uniq_notification_device_delivery",
            )
        ]
        indexes = [
            models.Index(fields=("status", "last_attempt_at"), name="notif_delivery_status_attempt"),
        ]

    def mark_sent(self, message_id: str = ""):
        now = timezone.now()
        self.status = self.Status.SENT
        self.attempt_count += 1
        self.last_attempt_at = now
        self.sent_at = now
        self.provider_message_id = message_id or ""
        self.last_error = ""
        self.save(
            update_fields=(
                "status",
                "attempt_count",
                "last_attempt_at",
                "sent_at",
                "provider_message_id",
                "last_error",
            )
        )

    def mark_failed(self, error: str):
        self.status = self.Status.FAILED
        self.attempt_count += 1
        self.last_attempt_at = timezone.now()
        self.last_error = error[:2000]
        self.save(update_fields=("status", "attempt_count", "last_attempt_at", "last_error"))
