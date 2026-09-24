from celery import shared_task

from payments.services.idempotency import prune_idempotency_keys


@shared_task(
    name="payments.tasks.purge_idempotency_keys",
    ignore_result=True,
)
def purge_idempotency_keys() -> int:
    return prune_idempotency_keys()
