from django.contrib.auth import get_user_model
from django.test import TestCase

from auditlog.models import AuditEvent


class AuditEventTests(TestCase):
    def test_audit_event_is_immutable_after_creation(self):
        user = get_user_model().objects.create_user(
            username="audit-user",
            email="audit@example.com",
            password="StrongPass123!",
        )
        event = AuditEvent.objects.create(
            actor=user,
            action="invoice.confirm",
            entity_type="Invoice",
            entity_id=1,
            metadata={"status": "confirmed"},
        )

        event.action = "invoice.cancel"
        with self.assertRaises(ValueError):
            event.save()

    def test_audit_event_can_be_created_without_an_actor(self):
        event = AuditEvent.objects.create(
            action="system.maintenance",
            entity_type="System",
            metadata={"job": "reconciliation"},
        )
        self.assertIsNone(event.actor_id)
