from core.middleware import get_current_request_id

from .models import AuditEvent


def record_event(*, action, entity_type, entity_id=None, actor_id=None, metadata=None):
    """Persist one immutable audit event inside the caller's transaction."""
    safe_metadata = metadata or {}
    if not isinstance(safe_metadata, dict):
        raise TypeError("Audit metadata must be a dictionary.")
    return AuditEvent.objects.create(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        request_id=get_current_request_id() or "",
        metadata=safe_metadata,
    )
