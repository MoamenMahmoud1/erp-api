"""Coupon validation and application for draft invoices."""

from django.db import transaction
from django.utils import timezone

from common.exceptions import CouponInvalid, InvalidStateTransition
from coupons.models import Coupon
from invoices.calculator import InvoiceCalculator

from .lifecycle import load_invoice_for_update

_calculator = InvoiceCalculator()


def _validate_coupon(coupon, invoice):
    if not coupon.is_active:
        raise CouponInvalid("Coupon is not active.")
    now = timezone.now()
    if coupon.valid_from and now < coupon.valid_from:
        raise CouponInvalid("Coupon is not yet valid.")
    if coupon.valid_until and now > coupon.valid_until:
        raise CouponInvalid("Coupon has expired.")
    if coupon.minimum_invoice_amount and _calculator.subtotal(invoice) < coupon.minimum_invoice_amount:
        raise CouponInvalid("The invoice does not meet the coupon's minimum amount.")


@transaction.atomic
def apply_coupon(*, invoice_id, code, actor=None):
    invoice = load_invoice_for_update(invoice_id, actor)
    if invoice.status != invoice.Status.DRAFT:
        raise InvalidStateTransition("A coupon can only be applied to a draft invoice.")
    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist as exc:
        raise CouponInvalid("Coupon not found.") from exc
    _validate_coupon(coupon, invoice)
    invoice.coupon = coupon
    invoice.coupon_discount = _calculator.coupon_discount_value(coupon, _calculator.subtotal(invoice))
    invoice.save(update_fields=("coupon", "coupon_discount", "updated_at"))
    return invoice


class ApplyCoupon:
    def __call__(self, *, invoice_id, code, actor=None):
        return apply_coupon(invoice_id=invoice_id, code=code, actor=actor)
