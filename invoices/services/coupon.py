"""Coupon validation and atomic application to draft invoices."""

from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

from common.exceptions import CouponInvalid, InvalidStateTransition
from coupons.models import Coupon
from invoices.calculator import InvoiceCalculator

from .lifecycle import load_invoice_for_update_sync

_calculator = InvoiceCalculator()


def _validate_coupon_sync(coupon, invoice):
    if not coupon.is_active:
        raise CouponInvalid("Coupon is not active.")
    now = timezone.now()
    if coupon.valid_from and now < coupon.valid_from:
        raise CouponInvalid("Coupon is not yet valid.")
    if coupon.valid_until and now > coupon.valid_until:
        raise CouponInvalid("Coupon has expired.")
    if coupon.minimum_invoice_amount:
        subtotal = _calculator.subtotal(invoice)
        if subtotal < coupon.minimum_invoice_amount:
            raise CouponInvalid(
                "The invoice does not meet the coupon's minimum amount."
            )


def _apply_coupon_sync(invoice_id, code):
    """Keep invoice locking, validation, calculation, and update atomic."""
    with transaction.atomic():
        invoice = load_invoice_for_update_sync(invoice_id)
        if invoice.status != invoice.Status.DRAFT:
            raise InvalidStateTransition(
                "A coupon can only be applied to a draft invoice."
            )
        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist as exc:
            raise CouponInvalid("Coupon not found.") from exc

        _validate_coupon_sync(coupon, invoice)
        invoice.coupon = coupon
        invoice.coupon_discount = _calculator.coupon_discount_value(
            coupon,
            _calculator.subtotal(invoice),
        )
        invoice.save(update_fields=("coupon", "coupon_discount", "updated_at"))
        return invoice


class ApplyCoupon:
    """Apply a coupon to a draft invoice atomically."""

    async def __call__(self, *, invoice_id, code):
        return await sync_to_async(
            _apply_coupon_sync,
            thread_sensitive=True,
        )(invoice_id, code)
