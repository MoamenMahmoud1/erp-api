from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIRequestFactory, force_authenticate

from products.api.views import (
    CartonPricingViewSet,
    ProductViewSet,
)
from products.models import CartonPricing, Product


class ProductAsyncViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="product_user",
            email="product@example.com",
            password="test-password",
        )

        self.staff_user = User.objects.create_user(
            username="product_staff",
            email="product_staff@example.com",
            password="test-password",
            is_staff=True,
        )

        self.product = Product.objects.create(
            name="Test Product",
            purchase_price=Decimal("100.00"),
            selling_price=Decimal("150.00"),
        )

        self.factory = APIRequestFactory()

    async def test_list_view_is_async(self):
        request = self.factory.get(
            reverse("products:product-list"),
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await ProductViewSet.as_view(
            {
                "get": "list",
            }
        )(
            request,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    async def test_detail_view_is_async(self):
        request = self.factory.get(
            reverse(
                "products:product-detail",
                kwargs={"pk": self.product.pk},
            ),
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await ProductViewSet.as_view(
            {
                "get": "retrieve",
            }
        )(
            request,
            pk=self.product.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    async def test_authenticated_user_cannot_create_product(self):
        request = self.factory.post(
            reverse("products:product-list"),
            {
                "name": "New Product",
                "purchase_price": "200.00",
                "selling_price": "300.00",
            },
            format="json",
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await ProductViewSet.as_view(
            {
                "post": "create",
            }
        )(
            request,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    async def test_staff_can_create_product(self):
        request = self.factory.post(
            reverse("products:product-list"),
            {
                "name": "New Product",
                "purchase_price": "200.00",
                "selling_price": "300.00",
            },
            format="json",
        )

        force_authenticate(
            request,
            user=self.staff_user,
        )

        response = await ProductViewSet.as_view(
            {
                "post": "create",
            }
        )(
            request,
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            await Product.objects.filter(
                name="New Product",
            ).aexists(),
        )

    async def test_authenticated_user_cannot_update_product(self):
        request = self.factory.patch(
            reverse(
                "products:product-detail",
                kwargs={"pk": self.product.pk},
            ),
            {
                "selling_price": "175.00",
            },
            format="json",
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await ProductViewSet.as_view(
            {
                "patch": "partial_update",
            }
        )(
            request,
            pk=self.product.pk,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    async def test_staff_can_update_product(self):
        request = self.factory.patch(
            reverse(
                "products:product-detail",
                kwargs={"pk": self.product.pk},
            ),
            {
                "selling_price": "175.00",
            },
            format="json",
        )

        force_authenticate(
            request,
            user=self.staff_user,
        )

        response = await ProductViewSet.as_view(
            {
                "patch": "partial_update",
            }
        )(
            request,
            pk=self.product.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        await self.product.arefresh_from_db()

        self.assertEqual(
            self.product.selling_price,
            Decimal("175.00"),
        )

    async def test_authenticated_user_cannot_delete_product(self):
        request = self.factory.delete(
            reverse(
                "products:product-detail",
                kwargs={"pk": self.product.pk},
            ),
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await ProductViewSet.as_view(
            {
                "delete": "destroy",
            }
        )(
            request,
            pk=self.product.pk,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    async def test_staff_can_delete_product(self):
        product = await Product.objects.acreate(
            name="Delete Product",
            purchase_price=Decimal("50.00"),
            selling_price=Decimal("75.00"),
        )

        request = self.factory.delete(
            reverse(
                "products:product-detail",
                kwargs={"pk": product.pk},
            ),
        )

        force_authenticate(
            request,
            user=self.staff_user,
        )

        response = await ProductViewSet.as_view(
            {
                "delete": "destroy",
            }
        )(
            request,
            pk=product.pk,
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            await Product.objects.filter(
                pk=product.pk,
            ).aexists(),
        )


class CartonPricingAsyncViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="carton_user",
            email="carton@example.com",
            password="test-password",
        )

        self.staff_user = User.objects.create_user(
            username="carton_staff",
            email="carton_staff@example.com",
            password="test-password",
            is_staff=True,
        )

        self.carton = CartonPricing.objects.create(
            name="Box",
            units_per_carton=12,
            carton_price=Decimal("1000.00"),
        )

        self.factory = APIRequestFactory()

    async def test_list_view_is_async(self):
        request = self.factory.get(
            reverse("products:cartonpricing-list"),
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await CartonPricingViewSet.as_view(
            {
                "get": "list",
            }
        )(
            request,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    async def test_detail_view_is_async(self):
        request = self.factory.get(
            reverse(
                "products:cartonpricing-detail",
                kwargs={"pk": self.carton.pk},
            ),
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await CartonPricingViewSet.as_view(
            {
                "get": "retrieve",
            }
        )(
            request,
            pk=self.carton.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    async def test_authenticated_user_cannot_create_carton_pricing(self):
        request = self.factory.post(
            reverse("products:cartonpricing-list"),
            {
                "name": "Large Box",
                "units_per_carton": 24,
                "carton_price": "1800.00",
            },
            format="json",
        )

        force_authenticate(
            request,
            user=self.user,
        )

        response = await CartonPricingViewSet.as_view(
            {
                "post": "create",
            }
        )(
            request,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    async def test_staff_can_create_carton_pricing(self):
        request = self.factory.post(
            reverse("products:cartonpricing-list"),
            {
                "name": "Large Box",
                "units_per_carton": 24,
                "carton_price": "1800.00",
            },
            format="json",
        )

        force_authenticate(
            request,
            user=self.staff_user,
        )

        response = await CartonPricingViewSet.as_view(
            {
                "post": "create",
            }
        )(
            request,
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            await CartonPricing.objects.filter(
                name="Large Box",
            ).aexists(),
        )

    async def test_staff_can_update_carton_pricing(self):
        request = self.factory.patch(
            reverse(
                "products:cartonpricing-detail",
                kwargs={"pk": self.carton.pk},
            ),
            {
                "carton_price": "1200.00",
            },
            format="json",
        )

        force_authenticate(
            request,
            user=self.staff_user,
        )

        response = await CartonPricingViewSet.as_view(
            {
                "patch": "partial_update",
            }
        )(
            request,
            pk=self.carton.pk,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        await self.carton.arefresh_from_db()

        self.assertEqual(
            self.carton.carton_price,
            Decimal("1200.00"),
        )

    async def test_staff_can_delete_carton_pricing(self):
        carton = await CartonPricing.objects.acreate(
            name="Delete Box",
            units_per_carton=6,
            carton_price=Decimal("500.00"),
        )

        request = self.factory.delete(
            reverse(
                "products:cartonpricing-detail",
                kwargs={"pk": carton.pk},
            ),
        )

        force_authenticate(
            request,
            user=self.staff_user,
        )

        response = await CartonPricingViewSet.as_view(
            {
                "delete": "destroy",
            }
        )(
            request,
            pk=carton.pk,
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            await CartonPricing.objects.filter(
                pk=carton.pk,
            ).aexists(),
        )