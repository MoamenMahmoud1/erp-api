from django.conf import settings
from django.db import models


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
