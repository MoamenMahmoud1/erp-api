import hashlib
import json
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from common.exceptions import InvalidBusinessOperation
from payments.models import IdempotencyKey


def request_signature(data):
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_or_create_key(*, key, user_id, path, data):
    signature = request_signature(data)
    existing = (
        IdempotencyKey.objects.select_for_update()
        .filter(key=key, user_id=user_id, path=path)
        .first()
    )
    if existing is not None:
        return existing, existing.request_signature == signature

    try:
        with transaction.atomic():
            record = IdempotencyKey.objects.create(
                key=key,
                user_id=user_id,
                path=path,
                request_signature=signature,
                response_status=0,
                response_body={},
            )
    except IntegrityError:
        winner = (
            IdempotencyKey.objects.select_for_update()
            .filter(key=key, user_id=user_id, path=path)
            .first()
        )
        if winner is None:
            raise InvalidBusinessOperation("Idempotency conflict — please retry.")
        return winner, winner.request_signature == signature

    return record, True


def prune_idempotency_keys(*, older_than=None):
    """Delete idempotency records older than the configured retention window.

    Call this from a scheduled maintenance process (cron/Celery/management
    command) so the hot table does not grow without bound.
    """
    cutoff = older_than or (
        timezone.now() - timedelta(days=settings.IDEMPOTENCY_RETENTION_DAYS)
    )
    deleted, _details = IdempotencyKey.objects.filter(created_at__lt=cutoff).delete()
    return deleted
