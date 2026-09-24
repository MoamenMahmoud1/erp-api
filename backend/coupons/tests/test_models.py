from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from coupons.models import Coupon


class CouponModelTests(TestCase):
    def test_percentage_discount_cannot_exceed_100(self):
        coupon = Coupon(
            code="over",
            discount_type=Coupon.DiscountType.PERCENTAGE,
            discount_value=Decimal("101"),
        )
        with self.assertRaises(ValidationError):
            coupon.full_clean()

    def test_valid_percentage_discount_is_allowed(self):
        coupon = Coupon(
            code="valid",
            discount_type=Coupon.DiscountType.PERCENTAGE,
            discount_value=Decimal("50"),
        )
        coupon.full_clean()

    def test_invalid_date_window_is_rejected(self):
        coupon = Coupon(
            code="dates",
            discount_type=Coupon.DiscountType.FIXED,
            discount_value=Decimal("5"),
            valid_from="2025-01-10T00:00:00Z",
            valid_until="2025-01-01T00:00:00Z",
        )
        with self.assertRaises(ValidationError):
            coupon.full_clean()

    def test_negative_discount_is_rejected_by_validation_and_database(self):
        coupon = Coupon(
            code="neg",
            discount_type=Coupon.DiscountType.FIXED,
            discount_value=Decimal("-5"),
        )
        with self.assertRaises(ValidationError):
            coupon.full_clean()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                created = Coupon.objects.create(
                    code="neg2",
                    discount_type=Coupon.DiscountType.FIXED,
                    discount_value=Decimal("0"),
                )
                Coupon.objects.filter(pk=created.pk).update(discount_value=Decimal("-5"))

    def test_percentage_over_100_is_rejected_by_database(self):
        coupon = Coupon.objects.create(
            code="perc",
            discount_type=Coupon.DiscountType.PERCENTAGE,
            discount_value=Decimal("10"),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Coupon.objects.filter(pk=coupon.pk).update(discount_value=Decimal("150"))
