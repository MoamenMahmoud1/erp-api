"""
Single authoritative source for invoice financial calculations.

The backend is the source of truth for invoice money. Serializers, views and
model properties must NOT implement the same formulas independently — they
delegate here.

Money convention (common.money): Decimal everywhere, ROUND_HALF_UP, 2dp,
no silent clamping, no floats.

A coupon's discount, when applied, is persisted as ``Invoice.coupon_discount``
(a snapshot). Historical totals stay stable even if the coupon is later
edited or deactivated.
"""

from decimal import Decimal

from common.exceptions import InvalidDiscount
from common.money import quantize_money


class InvoiceCalculator:
    def subtotal(self, invoice):
        """Sum of line totals: unit_price * quantity for every item."""
        return quantize_money(
            sum((item.line_total for item in invoice.items.all()), Decimal("0"))
        )

    def discount(self, invoice):
        """The authoritative discount snapshot persisted on the invoice."""
        return quantize_money(invoice.coupon_discount or Decimal("0"))

    def total(self, invoice):
        return quantize_money(self.subtotal(invoice) - self.discount(invoice))

    def coupon_discount_value(self, coupon, subtotal):
        """Compute the discount for a coupon against a subtotal.

        Percentage discounts are applied as subtotal * value / 100 (capped at
        the subtotal because value <= 100). Fixed discounts must not exceed the
        subtotal — that would create a negative total, which we reject rather
        than silently clamp.
        """
        from coupons.models import Coupon

        subtotal = quantize_money(subtotal)
        if coupon.discount_type == Coupon.DiscountType.PERCENTAGE:
            return quantize_money(subtotal * coupon.discount_value / Decimal("100"))

        fixed = quantize_money(coupon.discount_value)
        if fixed > subtotal:
            raise InvalidDiscount(
                "A fixed discount cannot exceed the invoice subtotal."
            )
        return fixed