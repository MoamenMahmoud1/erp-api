from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from auditlog.models import AuditEvent

from .models import Notification


@shared_task(
    name="notifications.tasks.create_notification_for_approval_event",
    ignore_result=True,
)
def create_notification_for_approval_event(approval_event_id: int) -> int:
    event = AuditEvent.objects.filter(
        pk=approval_event_id,
        action__in=("approval.requested", "approval.approved", "approval.rejected"),
    ).first()
    if event is None:
        return 0

    metadata = event.metadata or {}
    if event.action == "approval.requested":
        recipient_ids = [metadata.get("approver_id")]
        notification_type = Notification.NotificationType.APPROVAL_REQUESTED
        title = "طلب موافقة جديد"
        body = f"يوجد طلب {metadata.get('operation', '')} جديد يحتاج إلى موافقتك."
    elif event.action == "approval.approved":
        recipient_ids = [metadata.get("requester_id")]
        notification_type = Notification.NotificationType.APPROVAL_APPROVED
        title = "تمت الموافقة"
        body = f"تمت الموافقة على طلب {metadata.get('operation', '')}."
    else:
        recipient_ids = [metadata.get("requester_id")]
        notification_type = Notification.NotificationType.APPROVAL_REJECTED
        title = "تم رفض الطلب"
        body = f"تم رفض طلب {metadata.get('operation', '')}."

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
    event_ids = AuditEvent.objects.filter(
        created_at__gte=since,
        action__in=("approval.requested", "approval.approved", "approval.rejected"),
    ).values_list("id", flat=True)

    queued_count = 0
    for event_id in event_ids.iterator(chunk_size=200):
        create_notification_for_approval_event.delay(event_id)
        queued_count += 1
    return queued_count
