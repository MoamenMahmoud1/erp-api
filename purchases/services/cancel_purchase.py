from django.db import transaction

from common.exceptions import InvalidBusinessOperation, InvalidStateTransition
from purchases.models import Purchase


class CancelPurchaseService:
    @staticmethod
    @transaction.atomic
    def execute(*, purchase_id, actor):
        try:
            purchase = Purchase.objects.visible_to(actor).select_for_update().get(pk=purchase_id)
        except Purchase.DoesNotExist as exc:
            raise InvalidBusinessOperation("Purchase not found or not accessible.") from exc

        if purchase.status != Purchase.Status.DRAFT:
            raise InvalidStateTransition("Only draft purchases can be cancelled.")

        purchase.status = Purchase.Status.CANCELLED
        purchase.save(update_fields=("status", "updated_at"))
        return purchase
