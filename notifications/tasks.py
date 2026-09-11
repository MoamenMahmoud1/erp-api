from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from auditlog.models import AuditEvent

from .models import Notification


APPROVAL_ACTIONS = ("approval.requested", "approval.approved", "approval.rejected")


def _notification_details(event: AuditEvent):
    metadata = event.metadata or {}
    if event.action == "approval.requested":
        return [metadata.get("approver_id")], Notification.NotificationType.APPROVAL_REQUESTED, "طلب موافقة جديد", f"يوجد طلب {metadata.get('operation', '')} جديد يحتاج إلى موافقتك."
    if event.action == "approval.approved":
        return [metadata.get("requester_id")], Notification.NotificationType.APPROVAL_APPROVED, "تمت الموافقة", f"تمت الموافقة على طلب {metadata.get('operation', '')}."
    return [metadata.get("requester_id")], Notification.NotificationType.APPROVAL_REJECTED, "تم رفض الطلب", f"تم رفض طلب {metadata.get('operation', '')}."


@shared_task(
    name="notifications.tasks.create_notification_for_approval_event",
    ignore_result=True,
)
def create_notification_for_approval_event(approval_event_id: int) -> int:
    event = AuditEvent.objects.filter(
        pk=approval_event_id,
        action__in=APPROVAL_ACTIONS,
    ).first()
    if event is None:
        return 0

    metadata = event.metadata or {}
    recipient_ids, notification_type, title, body = _notification_details(event)
    created_count = 0

    for recipient_id in recipient_ids:
        if not recipient_id:
            continue
        _, created = Notification.objects.get_or_create(
            dedupe_key=f"approval:{event.pk}:{int(recipient_id)}",
            defaults={
                "user_id": int(recipient_id),
                "notification_type": notification_type,
                "title": title,
                "body": body,
                "target_type": event.entity_type,
                "target_id": event.entity_id,
                "data": {
                    "approval_event_id": event.pk,
                    "operation": metadata.get("operation"),
                    "requested_by": event.actor_id,
                    "approver_id": metadata.get("approver_id"),
                    "decision_reason": metadata.get("decision_reason", ""),
                },
            },
        )
        created_count += int(created)

    return created_count


@shared_task(
    name="notifications.tasks.rebuild_recent_approval_notifications",
    ignore_result=True,
)
def rebuild_recent_approval_notifications() -> int:
    since = timezone.now() - timedelta(days=7)
    events = AuditEvent.objects.filter(
        created_at__gte=since,
        action__in=APPROVAL_ACTIONS,
    ).only("id", "action", "actor_id", "entity_type", "entity_id", "metadata")

    queued_count = 0
    for event in events.iterator(chunk_size=200):
        recipient_ids, _, _, _ = _notification_details(event)
        for recipient_id in recipient_ids:
            if not recipient_id:
                continue
            dedupe_key = f"approval:{event.pk}:{int(recipient_id)}"
            if Notification.objects.filter(dedupe_key=dedupe_key).exists():
                continue
            create_notification_for_approval_event.delay(event.pk)
            queued_count += 1
            break
    return queued_count
