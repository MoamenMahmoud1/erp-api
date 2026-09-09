from django.db import transaction

from accounts.services.employee_shift import require_open_shift
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

        shift = require_open_shift(actor)
        if shift is not None and purchase.site_id != shift.site_id:
            raise InvalidBusinessOperation("The purchase belongs to a different site than the current shift.")
        if shift is not None and purchase.shift_id not in (None, shift.pk):
            raise InvalidBusinessOperation("The purchase was created in a different shift.")

        purchase.status = Purchase.Status.CANCELLED
        purchase.save(update_fields=("status", "updated_at"))
        return purchase
