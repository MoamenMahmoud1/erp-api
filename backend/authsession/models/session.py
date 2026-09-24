import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuthSession(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auth_sessions",
    )

    device_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        db_index=True,
    )
    device_name = models.CharField(max_length=100, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    current_refresh_jti = models.UUIDField(unique=True)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_refreshed_at = models.DateTimeField(default=timezone.now)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_authsession"
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=("user", "revoked_at"),
                name="accounts_auth_user_rev_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("user", "device_id"),
                condition=models.Q(revoked_at__isnull=True),
                name="authsession_one_active_device",
            ),
        ]

    @property
    def is_active(self):
        return (
            self.revoked_at is None
            and self.expires_at > timezone.now()
        )

    def __str__(self):
        device = self.device_name or self.device_id
        return f"{self.user} - {device}"
