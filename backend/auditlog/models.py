from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """Immutable record of a security- or money-sensitive business action."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_events",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.PositiveBigIntegerField(null=True, blank=True)
    request_id = models.CharField(max_length=128, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("entity_type", "entity_id", "created_at"), name="audit_entity_created_idx"),
            models.Index(fields=("actor", "created_at"), name="audit_actor_created_idx"),
            models.Index(fields=("action", "created_at"), name="audit_action_created_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Audit events are immutable.")
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.action} {self.entity_type}#{self.entity_id or '-'}"
