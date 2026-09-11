from dataclasses import dataclass

from django.db import transaction

from auditlog.models import AuditEvent

from .models import Notification
from .tasks import create_notification_for_approval_event


@dataclass(frozen=True)
class NotificationMessage:
    notification_type: str
    title: str
    body: str
    target_type: str
    target_id: int | None
    data: dict


def queue_approval_event_notification(event: AuditEvent) -> None:
    """Schedule notification fan-out only after the business transaction commits."""
    transaction.on_commit(lambda: create_notification_for_approval_event.delay(event.pk))


def build_approval_notification(event: AuditEvent, recipient_id: int) -> NotificationMessage | None:
    metadata = event.metadata or {}
    operation = metadata.get("operation", "")
    target_type = event.entity_type
    target_id = event.entity_id

    if event.action == "approval.requested":
        title = "طلب موافقة جديد"
        body = f"يوجد طلب {operation} جديد يحتاج إلى موافقتك."
        notification_type = Notification.NotificationType.APPROVAL_REQUESTED
    elif event.action == "approval.approved":
        title = "تمت الموافقة"
        body = f"تمت الموافقة على طلب {operation}."
        notification_type = Notification.NotificationType.APPROVAL_APPROVED
    elif event.action == "approval.rejected":
        title = "تم رفض الطلب"
        body = f"تم رفض طلب {operation}."
        notification_type = Notification.NotificationType.APPROVAL_REJECTED
    else:
        return None

    return NotificationMessage(
        notification_type=notification_type,
        title=title,
        body=body,
        target_type=target_type,
        target_id=target_id,
        data={
            "approval_event_id": event.pk,
            "operation": operation,
            "requested_by": event.actor_id,
            "approver_id": metadata.get("approver_id"),
            "decision_reason": metadata.get("decision_reason", ""),
        },
    )


def notification_recipient_ids(event: AuditEvent) -> list[int]:
    metadata = event.metadata or {}
    if event.action == "approval.requested":
        approver_id = metadata.get("approver_id")
        return [int(approver_id)] if approver_id else []
    if event.action in {"approval.approved", "approval.rejected"}:
        requester_id = metadata.get("requester_id")
        return [int(requester_id)] if requester_id else []
    return []
