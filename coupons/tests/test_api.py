from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from coupons.models import Coupon


class CouponAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="coupon_user",
            email="coupon@example.com",
            password="StrongPass123!",
        )
        self.staff_user = User.objects.create_user(
            username="coupon_staff",
            email="coupon_staff@example.com",
            password="StrongPass123!",
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
        self.assertEqual(self.client.get(reverse("coupons:coupon-list")).status_code, 200)
        response = self.client.get(reverse("coupons:coupon-detail", kwargs={"pk": self.coupon.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "SAVE10")

    def test_unauthenticated_is_rejected(self):
        self.assertEqual(self.client.get(reverse("coupons:coupon-list")).status_code, 401)

    def test_regular_user_cannot_write(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("coupons:coupon-list"),
            {
                "code": "NEW10",
                "discount_type": Coupon.DiscountType.PERCENTAGE,
                "discount_value": "10.00",
                "minimum_invoice_amount": "100.00",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_can_create_update_delete(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post(
            reverse("coupons:coupon-list"),
            {
                "code": "NEW10",
                "discount_type": Coupon.DiscountType.PERCENTAGE,
                "discount_value": "10.00",
                "minimum_invoice_amount": "100.00",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        coupon_id = response.data["id"]
        detail = reverse("coupons:coupon-detail", kwargs={"pk": coupon_id})
        self.assertEqual(self.client.patch(detail, {"discount_value": "20.00"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(detail).status_code, 204)

    def test_regular_user_cannot_update_or_delete(self):
        self.client.force_authenticate(user=self.user)
        detail = reverse("coupons:coupon-detail", kwargs={"pk": self.coupon.pk})
        self.assertEqual(self.client.patch(detail, {"discount_value": "20.00"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(detail).status_code, 403)
