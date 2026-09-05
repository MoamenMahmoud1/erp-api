from django.db import transaction

from common.exceptions import InvalidStateTransition

from .lifecycle import load_invoice_for_update


@transaction.atomic
def remove_coupon(invoice_id, actor=None):
    invoice = load_invoice_for_update(invoice_id, actor)
    if invoice.status != invoice.Status.DRAFT:
        raise InvalidStateTransition("A coupon can only be removed from a draft invoice.")
    invoice.coupon = None
    invoice.coupon_discount = 0
    invoice.save(update_fields=("coupon", "coupon_discount", "updated_at"))
    return invoice


class RemoveCoupon:
    def __call__(self, *, invoice_id, actor=None):
        return remove_coupon(invoice_id, actor)
