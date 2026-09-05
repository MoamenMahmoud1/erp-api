from django.db import transaction

from common.exceptions import InvalidStateTransition
from invoices.models import Invoice


def remove_coupon(invoice_id):
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
        if invoice.status != Invoice.Status.DRAFT:
            raise InvalidStateTransition("A coupon can only be removed from a draft invoice.")
        invoice.coupon = None
        invoice.coupon_discount = 0
        invoice.save(update_fields=("coupon", "coupon_discount", "updated_at"))
        return invoice


class RemoveCoupon:
    def __call__(self, *, invoice_id):
        return remove_coupon(invoice_id)
