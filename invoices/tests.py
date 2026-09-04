from decimal import Decimal

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase
from django.test.client import AsyncRequestFactory
from django.utils import timezone
from rest_framework.test import force_authenticate

from common.exceptions import (
    CouponInvalid,
    InsufficientStock,
    InvalidDiscount,
    InvalidStateTransition,
)
from coupons.models import Coupon
from customers.models import Customer
from inventory.models import (
    StockBalance,
    StockLocation,
    StockMovement,
    StockMovementItem,
)
from invoices.models import Invoice, InvoiceItem
from invoices.api.views import InvoiceViewSet
from invoices.services import (
    ApplyCoupon,
    CancelInvoice,
    ConfirmInvoice,
    CreateInvoice,
    InvoiceNotFound,
)
from products.models import Product


class BaseInvoiceTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="inv-staff",
            email="inv-staff@example.com",
            password="StrongPass123!",
            is_active=True,
            is_verified=True,
            is_staff=True,
        )
        self.customer = Customer.objects.create(name="Acme")
        self.product = Product.objects.create(
            name="Widget",
            purchase_price=Decimal("60.00"),
            selling_price=Decimal("100.00"),
        )
        self.vehicle = StockLocation.objects.create(
            name="Van 01",
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            employee=self.staff,
        )
        StockBalance.objects.create(
            location=self.vehicle,
            product=self.product,
            quantity=50,
        )

    async def call(self, service, **kwargs):
        return await service(**kwargs)

    async def run_sync(self, function, *args, **kwargs):
        return await sync_to_async(
            function,
            thread_sensitive=True,
        )(*args, **kwargs)

    def make_invoice(self, quantity=1):
        invoice = Invoice.objects.create(
            customer=self.customer,
            created_by=self.staff,
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            quantity=quantity,
            unit_price=self.product.selling_price,
        )
        return invoice

    def make_coupon(
        self,
        code="SAVE10",
        discount_type=Coupon.DiscountType.PERCENTAGE,
        discount_value=Decimal("10"),
        **kwargs,
    ):
        return Coupon.objects.create(
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            **kwargs,
        )


class InvoiceCreationTests(BaseInvoiceTest):
    async def test_create_snapshots_prices_for_multiple_items(self):
        other = await self.run_sync(Product.objects.create,
            name="Other",
            purchase_price=Decimal("15.00"),
            selling_price=Decimal("25.50"),
        )
        invoice = await self.call(
            CreateInvoice(),
            user=self.staff,
            validated_data={
                "customer": self.customer,
                "items": [
                    {"product": self.product, "quantity": 2},
                    {"product": other, "quantity": 3},
                ],
            },
        )

        items = await self.run_sync(lambda: list(invoice.items.order_by("product_id")))
        self.assertEqual(len(items), 2)
        self.assertEqual(
            await self.run_sync(lambda: invoice.subtotal),
            Decimal("276.50"),
        )
        self.assertEqual(
            await InvoiceItem.objects.filter(
                invoice=invoice,
                product=self.product,
            ).values_list("unit_price", flat=True).aget(),
            Decimal("100.00"),
        )
        self.assertEqual(
            await InvoiceItem.objects.filter(
                invoice=invoice,
                product=other,
            ).values_list("unit_price", flat=True).aget(),
            Decimal("25.50"),
        )

    async def test_failed_create_rolls_back_invoice_and_items(self):
        before = await Invoice.objects.acount()
        with self.assertRaises(IntegrityError):
            await self.call(
                CreateInvoice(),
                user=self.staff,
                validated_data={
                    "customer": self.customer,
                    "items": [
                        {"product": self.product, "quantity": 1},
                        {"product": self.product, "quantity": 2},
                    ],
                },
            )
        self.assertEqual(await Invoice.objects.acount(), before)
        self.assertEqual(await InvoiceItem.objects.acount(), 0)


class InvoiceLifecycleTests(BaseInvoiceTest):
    async def test_draft_can_be_confirmed(self):
        invoice = await self.run_sync(self.make_invoice)
        returned = await self.call(ConfirmInvoice(), invoice_id=invoice.pk)
        self.assertEqual(returned.status, Invoice.Status.CONFIRMED)

    async def test_draft_and_confirmed_invoices_can_be_cancelled(self):
        draft = await self.run_sync(self.make_invoice)
        await self.call(CancelInvoice(), invoice_id=draft.pk)
        self.assertEqual(
            (await Invoice.objects.aget(pk=draft.pk)).status,
            Invoice.Status.CANCELLED,
        )

        confirmed = await self.run_sync(self.make_invoice)
        await self.call(ConfirmInvoice(), invoice_id=confirmed.pk)
        await self.call(CancelInvoice(), invoice_id=confirmed.pk)
        self.assertEqual(
            (await Invoice.objects.aget(pk=confirmed.pk)).status,
            Invoice.Status.CANCELLED,
        )

    async def test_invalid_transitions_and_missing_invoice_are_rejected(self):
        invoice = await self.run_sync(self.make_invoice)
        await self.call(CancelInvoice(), invoice_id=invoice.pk)
        with self.assertRaises(InvalidStateTransition):
            await self.call(ConfirmInvoice(), invoice_id=invoice.pk)
        with self.assertRaises(InvoiceNotFound):
            await self.call(ConfirmInvoice(), invoice_id=999999)


class InvoiceCouponTests(BaseInvoiceTest):
    async def test_valid_percentage_coupon_is_snapshotted(self):
        invoice = await self.run_sync(self.make_invoice, quantity=3)
        coupon = await self.run_sync(
            self.make_coupon,
            code="PCT",
            discount_value=Decimal("33.33"),
        )
        await self.call(ApplyCoupon(), invoice_id=invoice.pk, code=coupon.code)

        await invoice.arefresh_from_db()
        self.assertEqual(invoice.coupon_discount, Decimal("99.99"))
        self.assertEqual(await self.run_sync(lambda: invoice.total), Decimal("200.01"))

        await self.run_sync(setattr, coupon, "discount_value", Decimal("50"))
        await coupon.asave()
        await invoice.arefresh_from_db()
        self.assertEqual(invoice.coupon_discount, Decimal("99.99"))

    async def test_invalid_coupon_rules_are_rejected(self):
        invoice = await self.run_sync(self.make_invoice)
        cases = (
            await self.run_sync(self.make_coupon, code="INACTIVE", is_active=False),
            await self.run_sync(
                self.make_coupon,
                code="EXPIRED",
                valid_from=timezone.now() - timezone.timedelta(days=2),
                valid_until=timezone.now() - timezone.timedelta(days=1),
            ),
            await self.run_sync(
                self.make_coupon,
                code="FUTURE",
                valid_from=timezone.now() + timezone.timedelta(days=1),
            ),
            await self.run_sync(
                self.make_coupon,
                code="MIN",
                minimum_invoice_amount=Decimal("500"),
            ),
        )
        for coupon in cases:
            with self.subTest(coupon=coupon.code), self.assertRaises(CouponInvalid):
                await self.call(
                    ApplyCoupon(),
                    invoice_id=invoice.pk,
                    code=coupon.code,
                )
        with self.assertRaises(CouponInvalid):
            await self.call(ApplyCoupon(), invoice_id=invoice.pk, code="missing")

    async def test_fixed_discount_larger_than_subtotal_is_rejected(self):
        invoice = await self.run_sync(self.make_invoice)
        coupon = await self.run_sync(
            self.make_coupon,
            code="BIG",
            discount_type=Coupon.DiscountType.FIXED,
            discount_value=Decimal("150"),
        )
        with self.assertRaises(InvalidDiscount):
            await self.call(ApplyCoupon(), invoice_id=invoice.pk, code=coupon.code)

    async def test_coupon_cannot_be_applied_to_confirmed_invoice(self):
        invoice = await self.run_sync(self.make_invoice)
        await self.call(ConfirmInvoice(), invoice_id=invoice.pk)
        coupon = await self.run_sync(self.make_coupon)
        with self.assertRaises(InvalidStateTransition):
            await self.call(ApplyCoupon(), invoice_id=invoice.pk, code=coupon.code)


class InvoiceConfirmationInventoryTests(BaseInvoiceTest):
    async def test_confirmation_decreases_vehicle_stock_and_creates_sale_movement(
        self,
    ):
        invoice = await self.run_sync(self.make_invoice, quantity=20)

        await self.call(ConfirmInvoice(), invoice_id=invoice.pk)

        balance = await StockBalance.objects.filter(
            location=self.vehicle,
            product=self.product,
        ).aget()
        self.assertEqual(balance.quantity, 30)

        movement = await StockMovement.objects.filter(
            movement_type=StockMovement.MovementType.SALE,
            source_location=self.vehicle,
        ).aget()
        self.assertEqual(movement.reference, f"Invoice #{invoice.pk}")

        item = await StockMovementItem.objects.filter(
            movement=movement,
            product=self.product,
        ).aget()
        self.assertEqual(item.quantity, 20)

    async def test_confirmation_rejects_insufficient_stock_and_rolls_back(self):
        invoice = await self.run_sync(self.make_invoice, quantity=500)

        with self.assertRaises(InsufficientStock):
            await self.call(ConfirmInvoice(), invoice_id=invoice.pk)

        status = (await Invoice.objects.aget(pk=invoice.pk)).status
        self.assertEqual(status, Invoice.Status.DRAFT)
        self.assertFalse(
            await StockBalance.objects.filter(
                location=self.vehicle,
                product=self.product,
                quantity__lt=50,
            ).aexists()
        )
        self.assertFalse(await StockMovement.objects.aexists())
        self.assertFalse(await StockMovementItem.objects.aexists())

    async def test_sale_movement_and_stock_roll_back_together(self):
        second = await self.run_sync(
            Product.objects.create,
            name="Second Product",
            purchase_price=Decimal("10.00"),
            selling_price=Decimal("20.00"),
        )

        def _make_multi_invoice():
            inv = Invoice.objects.create(
                customer=self.customer,
                created_by=self.staff,
            )
            InvoiceItem.objects.create(
                invoice=inv,
                product=self.product,
                quantity=5,
                unit_price=self.product.selling_price,
            )
            InvoiceItem.objects.create(
                invoice=inv,
                product=second,
                quantity=3,
                unit_price=second.selling_price,
            )
            return inv

        # First product has stock, second does not — confirmation must roll back all.
        invoice = await self.run_sync(_make_multi_invoice)

        with self.assertRaises(InsufficientStock):
            await self.call(ConfirmInvoice(), invoice_id=invoice.pk)

        first_balance = await StockBalance.objects.filter(
            location=self.vehicle,
            product=self.product,
        ).aget()
        self.assertEqual(first_balance.quantity, 50)
        self.assertFalse(await StockMovement.objects.aexists())
        self.assertEqual(
            (await Invoice.objects.aget(pk=invoice.pk)).status,
            Invoice.Status.DRAFT,
        )


class InvoiceAPITests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="api-staff",
            email="api-staff@example.com",
            password="StrongPass123!",
            is_active=True,
            is_verified=True,
            is_staff=True,
        )
        self.customer = Customer.objects.create(name="Chris")
        self.product = Product.objects.create(
            name="Gadget",
            purchase_price=Decimal("40.00"),
            selling_price=Decimal("80.00"),
        )
        self.vehicle = StockLocation.objects.create(
            name="Van 02",
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            employee=self.staff,
        )
        StockBalance.objects.create(
            location=self.vehicle,
            product=self.product,
            quantity=30,
        )
        self.coupon = Coupon.objects.create(
            code="SAVE",
            discount_type=Coupon.DiscountType.PERCENTAGE,
            discount_value=Decimal("10"),
        )
        self.factory = AsyncRequestFactory()

    async def create_invoice(self):
        request = self.factory.post(
            "/api/v1/invoices/",
            {
                "customer": self.customer.pk,
                "items": [{"product": self.product.pk, "quantity": 1}],
            },
            content_type="application/json",
        )
        force_authenticate(request, user=self.staff)
        response = await InvoiceViewSet.as_view({"post": "acreate"})(request)
        self.assertEqual(response.status_code, 201)
        return response.data["id"]

    async def test_create_and_lifecycle_endpoints(self):
        pk = await self.create_invoice()
        request = self.factory.post(f"/api/v1/invoices/{pk}/confirm/", data={})
        force_authenticate(request, user=self.staff)
        response = await InvoiceViewSet.as_view({"post": "confirm"})(
            request,
            pk=pk,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Invoice.Status.CONFIRMED)

        request = self.factory.post(f"/api/v1/invoices/{pk}/cancel/", data={})
        force_authenticate(request, user=self.staff)
        response = await InvoiceViewSet.as_view({"post": "cancel"})(
            request,
            pk=pk,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Invoice.Status.CANCELLED)

    async def test_coupon_and_immutability_endpoints(self):
        pk = await self.create_invoice()
        request = self.factory.post(
            f"/api/v1/invoices/{pk}/apply-coupon/",
            {"code": self.coupon.code},
            content_type="application/json",
        )
        force_authenticate(request, user=self.staff)
        response = await InvoiceViewSet.as_view({"post": "apply_coupon"})(
            request,
            pk=pk,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["coupon_discount"], "8.00")

        request = self.factory.patch(
            f"/api/v1/invoices/{pk}/",
            {"status": "cancelled"},
            content_type="application/json",
        )
        force_authenticate(request, user=self.staff)
        response = await InvoiceViewSet.as_view({"patch": "partial_aupdate"})(
            request,
            pk=pk,
        )
        self.assertEqual(response.status_code, 405)

    async def test_invalid_input_and_missing_resources_return_client_errors(self):
        request = self.factory.post(
            "/api/v1/invoices/",
            {"customer": self.customer.pk, "items": []},
            content_type="application/json",
        )
        force_authenticate(request, user=self.staff)
        response = await InvoiceViewSet.as_view({"post": "acreate"})(request)
        self.assertEqual(response.status_code, 400)

        request = self.factory.post("/api/v1/invoices/999999/confirm/", data={})
        force_authenticate(request, user=self.staff)
        response = await InvoiceViewSet.as_view({"post": "confirm"})(
            request,
            pk=999999,
        )
        self.assertEqual(response.status_code, 404)

        pk = await self.create_invoice()
        request = self.factory.post(
            f"/api/v1/invoices/{pk}/apply-coupon/",
            {"code": "missing"},
            content_type="application/json",
        )
        force_authenticate(request, user=self.staff)
        response = await InvoiceViewSet.as_view({"post": "apply_coupon"})(
            request,
            pk=pk,
        )
        self.assertEqual(response.status_code, 400)
