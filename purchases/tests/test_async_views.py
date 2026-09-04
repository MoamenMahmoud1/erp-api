from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.test.client import AsyncRequestFactory
from django.urls import reverse
from rest_framework.test import force_authenticate

from inventory.models import StockLocation
from products.models import Product
from purchases.api.views import (
    PurchaseCancelView,
    PurchaseConfirmView,
    PurchaseDeleteView,
    PurchaseDetailView,
    PurchaseListCreateView,
)
from purchases.models import Purchase, PurchaseItem
from suppliers.models import Supplier


class PurchaseAsyncViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="async_purchase_user",
            email="async_purchase@example.com",
            password="test-password",
        )

        permissions = Permission.objects.filter(
            content_type__app_label="purchases",
            codename__in=(
                "view_purchase",
                "add_purchase",
                "change_purchase",
                "delete_purchase",
                "confirm_purchase",
                "cancel_purchase",
            ),
        )

        self.user.user_permissions.set(permissions)

        self.supplier = Supplier.objects.create(
            name="Async Test Supplier",
        )

        self.product = Product.objects.create(
            name="Async Test Product",
            purchase_price=Decimal("100.00"),
            selling_price=Decimal("150.00"),
        )

        self.warehouse = StockLocation.objects.create(
            name="Async Main Warehouse",
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
        )

        self.purchase = Purchase.objects.create(
            supplier=self.supplier,
            created_by=self.user,
            reference="PO-ASYNC-001",
        )

        PurchaseItem.objects.create(
            purchase=self.purchase,
            product=self.product,
            quantity=5,
            unit_purchase_price=Decimal("100.00"),
        )

        self.factory = AsyncRequestFactory()

    async def test_list_view_is_async(self):
        request = self.factory.get(
            reverse("purchase-list-create"),
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await PurchaseListCreateView.as_view()(
            request,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    async def test_detail_view_is_async(self):
        request = self.factory.get(
            reverse(
                "purchase-detail",
                kwargs={"pk": self.purchase.pk},
            ),
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await PurchaseDetailView.as_view()(
            request,
            pk=self.purchase.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    async def test_confirm_view_is_async(self):
        request = self.factory.post(
            reverse(
                "purchase-confirm",
                kwargs={"pk": self.purchase.pk},
            ),
            data={},
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await PurchaseConfirmView.as_view()(
            request,
            pk=self.purchase.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        await self.purchase.arefresh_from_db()

        self.assertEqual(
            self.purchase.status,
            Purchase.Status.CONFIRMED,
        )

    async def test_cancel_view_is_async(self):
        request = self.factory.post(
            reverse(
                "purchase-cancel",
                kwargs={"pk": self.purchase.pk},
            ),
            data={},
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await PurchaseCancelView.as_view()(
            request,
            pk=self.purchase.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        await self.purchase.arefresh_from_db()

        self.assertEqual(
            self.purchase.status,
            Purchase.Status.CANCELLED,
        )

    async def test_delete_view_is_async(self):
        request = self.factory.delete(
            reverse(
                "purchase-delete",
                kwargs={"pk": self.purchase.pk},
            ),
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await PurchaseDeleteView.as_view()(
            request,
            pk=self.purchase.pk,
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            await Purchase.objects.filter(
                pk=self.purchase.pk,
            ).aexists(),
        )