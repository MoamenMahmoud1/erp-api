import json
from decimal import Decimal

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase
from django.test.client import AsyncRequestFactory
from django.urls import resolve, reverse
from rest_framework.test import force_authenticate

from coupons.api.views import CouponViewSet
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

                Coupon.objects.filter(
                    code="neg2",
                ).update(
                    discount_value=Decimal("-5"),
                )

    def test_percentage_above_100_rejected_at_database(self):
        coupon = Coupon.objects.create(
            code="perc",
            discount_type=Coupon.DiscountType.PERCENTAGE,
            discount_value=Decimal("10"),
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Coupon.objects.filter(
                    pk=coupon.pk,
                ).update(
                    discount_value=Decimal("150"),
                )


class CouponAsyncViewsTests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="coupon_user",
            email="coupon@example.com",
            password="test-password",
            is_staff=False,
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

        self.factory = AsyncRequestFactory()

    async def test_list_view_is_async(self):
        request = self.factory.get(
            reverse("coupons:coupon-list"),
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await CouponViewSet.as_view(
            {"get": "list"},
        )(
            request,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    async def test_retrieve_view_is_async(self):
        request = self.factory.get(
            reverse(
                "coupons:coupon-detail",
                kwargs={"pk": self.coupon.pk},
            ),
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await CouponViewSet.as_view(
            {"get": "retrieve"},
        )(
            request,
            pk=self.coupon.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["code"],
            "SAVE10",
        )

    async def test_unauthenticated_user_is_rejected(self):
        request = self.factory.get(
            reverse("coupons:coupon-list"),
        )

        response = await CouponViewSet.as_view(
            {"get": "list"},
        )(
            request,
        )

        self.assertEqual(
            response.status_code,
            401,
        )
    async def test_authenticated_user_can_read(self):
        request = self.factory.get(
            reverse("coupons:coupon-list"),
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await CouponViewSet.as_view(
            {"get": "list"},
        )(
            request,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    async def test_regular_user_cannot_create_coupon(self):
        payload = {
            "code": "NEW10",
            "discount_type": Coupon.DiscountType.PERCENTAGE,
            "discount_value": "10.00",
            "minimum_invoice_amount": "100.00",
            "is_active": True,
        }

        request = self.factory.post(
            reverse("coupons:coupon-list"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await CouponViewSet.as_view(
            {"post": "create"},
        )(
            request,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    async def test_staff_can_create_coupon(self):
        payload = {
            "code": "NEW10",
            "discount_type": Coupon.DiscountType.PERCENTAGE,
            "discount_value": "10.00",
            "minimum_invoice_amount": "100.00",
            "is_active": True,
        }

        request = self.factory.post(
            reverse("coupons:coupon-list"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        force_authenticate(
            request,
            user=self.staff_user,
        )

        response = await CouponViewSet.as_view(
            {"post": "create"},
        )(
            request,
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            await Coupon.objects.filter(
                code="NEW10",
            ).aexists(),
        )

    async def test_staff_can_update_coupon(self):
        payload = {
            "discount_value": "20.00",
        }

        request = self.factory.patch(
            reverse(
                 "coupons:coupon-detail",
                    kwargs={"pk": self.coupon.pk},
                ),
            data=json.dumps(payload),
            content_type="application/json",
        )

        force_authenticate(
            request,
            user=self.staff_user,
        )

        response = await CouponViewSet.as_view(
            {"patch": "partial_update"},
        )(
            request,
            pk=self.coupon.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        await self.coupon.arefresh_from_db()

        self.assertEqual(
            self.coupon.discount_value,
            Decimal("20.00"),
        )

    async def test_regular_user_cannot_update_coupon(self):
        payload = {
            "discount_value": "20.00",
        }

        request = self.factory.patch(
            reverse(
                    "coupons:coupon-detail",
                    kwargs={"pk": self.coupon.pk},
                ),
            data=json.dumps(payload),
            content_type="application/json",
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await CouponViewSet.as_view(
            {"patch": "partial_update"},
        )(
            request,
            pk=self.coupon.pk,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    async def test_staff_can_delete_coupon(self):
        coupon_id = self.coupon.pk

        request = self.factory.delete(
            reverse(
               "coupons:coupon-detail",
               kwargs={"pk": self.coupon.pk},
                ),
       )

        force_authenticate(
            request,
            user=self.staff_user,
        )

        response = await CouponViewSet.as_view(
            {"delete": "destroy"},
        )(
            request,
            pk=coupon_id,
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            await Coupon.objects.filter(
                pk=coupon_id,
            ).aexists(),
        )

    async def test_regular_user_cannot_delete_coupon(self):
        coupon_id = self.coupon.pk

        request = self.factory.delete(
            reverse(
                "coupons:coupon-detail",
                kwargs={"pk": self.coupon.pk},
            ),
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await CouponViewSet.as_view(
            {"delete": "destroy"},
        )(
            request,
            pk=coupon_id,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertTrue(
            await Coupon.objects.filter(
                pk=coupon_id,
            ).aexists(),
        )

    async def test_invalid_percentage_returns_400(self):
        payload = {
            "code": "BAD100",
            "discount_type": Coupon.DiscountType.PERCENTAGE,
            "discount_value": "101.00",
            "is_active": True,
        }

        request = self.factory.post(
            reverse("coupons:coupon-list"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        force_authenticate(
            request,
            user=self.staff_user,
        )

        response = await CouponViewSet.as_view(
            {"post": "create"},
        )(
            request,
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertFalse(
            await Coupon.objects.filter(
                code="BAD100",
            ).aexists(),
        )

    async def test_search_by_code(self):
        request = self.factory.get(
            reverse("coupons:coupon-list"),
            data={"search": "SAVE10"},
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await CouponViewSet.as_view(
            {"get": "list"},
        )(
            request,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

    async def test_router_binds_async_lifecycle_actions(self):
        list_view = resolve(reverse("coupons:coupon-list")).func
        detail_view = resolve(
            reverse("coupons:coupon-detail", kwargs={"pk": self.coupon.pk})
        ).func

        self.assertEqual(list_view.actions["get"], "alist")
        self.assertEqual(list_view.actions["post"], "acreate")
        self.assertEqual(detail_view.actions["get"], "aretrieve")
        self.assertEqual(detail_view.actions["put"], "aupdate")
        self.assertEqual(detail_view.actions["patch"], "partial_aupdate")
        self.assertEqual(detail_view.actions["delete"], "adestroy")

    async def test_routed_staff_can_create_coupon(self):
        payload = {
            "code": "ROUTED10",
            "discount_type": Coupon.DiscountType.PERCENTAGE,
            "discount_value": "10.00",
        }
        request = self.factory.post(
            reverse("coupons:coupon-list"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        force_authenticate(request, user=self.staff_user)

        response = await resolve(reverse("coupons:coupon-list")).func(request)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            await Coupon.objects.filter(code="ROUTED10").aexists(),
        )

    async def test_routed_delete_returns_controlled_error_for_invoice_coupon(self):
        customer = await sync_to_async(
            Customer.objects.create,
            thread_sensitive=True,
        )(name="Coupon Customer")
        await sync_to_async(
            Invoice.objects.create,
            thread_sensitive=True,
        )(
            customer=customer,
            created_by=self.staff_user,
            coupon=self.coupon,
        )

        request = self.factory.delete(
            reverse("coupons:coupon-detail", kwargs={"pk": self.coupon.pk}),
        )
        force_authenticate(request, user=self.staff_user)

        response = await resolve(
            reverse("coupons:coupon-detail", kwargs={"pk": self.coupon.pk})
        ).func(request, pk=self.coupon.pk)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "coupon_in_use")
        self.assertTrue(await Coupon.objects.filter(pk=self.coupon.pk).aexists())
