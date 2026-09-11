import json
from dataclasses import dataclass
from typing import Callable

from django.db import transaction

from payments.models import IdempotencyKey
from payments.services.idempotency import load_or_create_key


@dataclass(frozen=True)
class IdempotentResult:
    status: int
    body: dict


def _json_safe(value):
    return json.loads(json.dumps(value, default=str))


@transaction.atomic
def execute_idempotent(*, key, user_id, path, data, operation: Callable[[], IdempotentResult]):
    """Run one state-changing HTTP operation exactly once for a key.

    The idempotency record and the operation share the same database
    transaction, so a process crash cannot commit the business mutation while
    leaving an empty idempotency response behind.
    """
    record, matches = load_or_create_key(
        key=key,
        user_id=user_id,
        path=path,
        data=data,
    )
    if not matches:
        return "mismatch"
    if record.response_status:
        return record

    result = operation()
    response_body = _json_safe(result.body)
    IdempotencyKey.objects.filter(pk=record.pk).update(
        response_status=result.status,
        response_body=response_body,
    )
    record.response_status = result.status
    record.response_body = response_body
    return record


def require_idempotency_key(request):
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key:
        return None
    if len(key) > 128:
        return None
    return key
