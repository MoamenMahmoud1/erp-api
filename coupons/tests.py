from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from coupons.models import Coupon
from customers.models import Customer
from invoices.models import Invoice


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

    def test_valid_until_must_be_after_valid_from(self):
        coupon = Coupon(
            code="dates",
            discount_type=Coupon.DiscountType.FIXED,
            discount_value=Decimal("5"),
            valid_from="2025-01-10T00:00:00Z",
            valid_until="2025-01-01T00:00:00Z",
        )
        with self.assertRaises(ValidationError):
            coupon.full_clean()

    def test_negative_discount_value_blocked_at_database(self):
        coupon = Coupon(
            code="neg",
            discount_type=Coupon.DiscountType.FIXED,
            discount_value=Decimal("-5"),
        )
        with self.assertRaises(ValidationError):
            coupon.full_clean()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Coupon.objects.create(
                    code="neg2",
                    discount_type=Coupon.DiscountType.FIXED,
                    discount_value=Decimal("0"),
                )
                Coupon.objects.filter(code="neg2").update(
                    discount_value=Decimal("-5")
                )

    def test_percentage_above_100_rejected_at_database(self):
        coupon = Coupon.objects.create(
            code="perc",
            discount_type=Coupon.DiscountType.PERCENTAGE,
            discount_value=Decimal("10"),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Coupon.objects.filter(pk=coupon.pk).update(
                    discount_value=Decimal("150")
                )


class CouponAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="coupon_user",
            email="coupon@example.com",
            password="test-password",
        )
        self.staff_user = User.objects.create_user(
            username="coupon_staff",
            email="coupon_staff@example.com",
            password="test-password",
            is_staff=True,
        )
        self.coupon = Coupon.objects.create(
            code="SAVE10",
            discount_type=Coupon.DiscountType.PERCENTAGE,
            discount_value=Decimal("10"),
            minimum_invoice_amount=Decimal("100"),
            is_active=True,
        )
        self.client = APIClient()

    def test_list_and_retrieve(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("coupons:coupon-list"))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse(
                "coupons:coupon-detail",
                kwargs={"pk": self.coupon.pk},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "SAVE10")

    def test_unauthenticated_user_is_rejected(self):
        response = self.client.get(reverse("coupons:coupon-list"))
        self.assertEqual(response.status_code, 401)

    def test_regular_user_cannot_write(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "code": "NEW10",
            "discount_type": Coupon.DiscountType.PERCENTAGE,
            "discount_value": "10.00",
            "minimum_invoice_amount": "100.00",
            "is_active": True,
        }
        response = self.client.post(
            reverse("coupons:coupon-list"),
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_can_create_update_delete(self):
        self.client.force_authenticate(user=self.staff_user)
        payload = {
            "code": "NEW10",
            "discount_type": Coupon.DiscountType.PERCENTAGE,
            "discount_value": "10.00",
            "minimum_invoice_amount": "100.00",
            "is_active": True,
        }
        response = self.client.post(
            reverse("coupons:coupon-list"),
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        coupon_id = response.data["id"]

        detail_url = reverse(
            "coupons:coupon-detail",
            kwargs={"pk": coupon_id},
        )
        response = self.client.patch(
            detail_url,
            {"discount_value": "20.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Coupon.objects.filter(pk=coupon_id).exists())

    def test_regular_user_cannot_update_or_delete(self):
        self.client.force_authenticate(user=self.user)
        detail_url = reverse(
            "coupons:coupon-detail",
            kwargs={"pk": self.coupon.pk},
        )
        response = self.client.patch(
            detail_url,
            {"discount_value": "20.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Coupon.objects.filter(pk=self.coupon.pk).exists())

    def test_invalid_percentage_returns_400(self):
        self.client.force_authenticate(user=self.staff_user)
        payload = {
            "code": "BAD100",
            "discount_type": Coupon.DiscountType.PERCENTAGE,
            "discount_value": "101.00",
            "is_active": True,
        }
        response = self.client.post(
            reverse("coupons:coupon-list"),
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Coupon.objects.filter(code="BAD100").exists())

    def test_search_by_code(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("coupons:coupon-list"),
            {"search": "SAVE10"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_referenced_coupon_cannot_be_deleted(self):
        customer = Customer.objects.create(name="Coupon Customer")
        Invoice.objects.create(
            customer=customer,
            created_by=self.staff_user,
            coupon=self.coupon,
        )
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.delete(
            reverse(
                "coupons:coupon-detail",
                kwargs={"pk": self.coupon.pk},
            )
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "coupon_in_use")
        self.assertTrue(Coupon.objects.filter(pk=self.coupon.pk).exists())
