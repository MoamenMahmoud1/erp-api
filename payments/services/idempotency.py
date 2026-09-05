import hashlib
import json

from django.db import IntegrityError, transaction

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
