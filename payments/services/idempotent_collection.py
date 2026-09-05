from django.db import transaction

from payments.api.serializers import PaymentTransactionSerializer
from payments.models import IdempotencyKey
from payments.services.collection import collect
from payments.services.idempotency import load_or_create_key


@transaction.atomic
def process_idempotent(*, key, user_id, path, data, customer, cash_amount, transfer_amount, actor=None):
    record, matches = load_or_create_key(key=key, user_id=user_id, path=path, data=data)
    if not matches:
        return "mismatch"
    if record.response_status:
        return record

    payment = collect(
        customer=customer,
        cash_amount=cash_amount,
        transfer_amount=transfer_amount,
        collected_by_id=user_id,
        actor=actor,
    )
    if payment is None:
        status_code = 200
        response_body = {"detail": "Zero-value collection is a no-op.", "code": "noop"}
    else:
        status_code = 201
        response_body = PaymentTransactionSerializer(payment).data

    IdempotencyKey.objects.filter(pk=record.pk).update(
        response_status=status_code,
        response_body=response_body,
    )
    record.response_status = status_code
    record.response_body = response_body
    return record
