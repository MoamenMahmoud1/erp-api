from asgiref.sync import sync_to_async
from django.db import transaction

from purchases.models import Purchase


class CancelPurchaseService:
    @staticmethod
    @transaction.atomic
    def execute(*, purchase_id):
        purchase = (
            Purchase.objects
            .select_for_update()
            .get(pk=purchase_id)
        )

        if purchase.status != Purchase.Status.DRAFT:
            raise ValueError(
                "Only draft purchases can be cancelled."
            )

        purchase.status = Purchase.Status.CANCELLED
        purchase.save(
            update_fields=["status", "updated_at"],
        )

        return purchase

    @staticmethod
    async def aexecute(*, purchase_id):
        return await sync_to_async(
            CancelPurchaseService.execute,
            thread_sensitive=True,
        )(purchase_id=purchase_id)