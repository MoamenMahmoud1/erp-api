from django.db import transaction

from accounts.services.employee_shift import require_open_shift
from common.exceptions import InvalidBusinessOperation, InvalidStateTransition

from .lifecycle import load_invoice_for_update


@transaction.atomic
def remove_coupon(invoice_id, actor=None):
    invoice = load_invoice_for_update(invoice_id, actor)
    if invoice.status != invoice.Status.DRAFT:
        raise InvalidStateTransition("A coupon can only be removed from a draft invoice.")
    shift = require_open_shift(actor) if actor is not None else None
    if shift is not None and invoice.site_id != shift.site_id:
        raise InvalidBusinessOperation("The invoice belongs to a different site than the current shift.")
    invoice.coupon = None
    invoice.coupon_discount = 0
    invoice.save(update_fields=("coupon", "coupon_discount", "updated_at"))
    return invoice


class RemoveCoupon:
    def __call__(self, *, invoice_id, actor=None):
        return remove_coupon(invoice_id, actor)
