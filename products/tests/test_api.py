from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from products.models import CartonPricing, Product


class ProductAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="product-user",
            email="product@example.com",
            password="StrongPass123!",
        )
        self.staff = User.objects.create_user(
            username="product-staff",
            email="product-staff@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.product = Product.objects.create(
            name="Test Product",
            purchase_price=Decimal("100"),
            selling_price=Decimal("150"),
        )
        self.client = APIClient()

    def test_authenticated_user_can_read_only(self):
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.get(reverse("products:product-list")).status_code, 200)
        self.assertEqual(
            self.client.patch(
                reverse("products:product-detail", kwargs={"pk": self.product.pk}),
                {"selling_price": "175.00"},
                format="json",
            ).status_code,
            403,
        )

    def test_staff_can_write_and_archive(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            reverse("products:product-list"),
            {"name": "New", "purchase_price": "200", "selling_price": "300"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        product_id = response.data["id"]
        response = self.client.patch(
            reverse("products:product-detail", kwargs={"pk": product_id}),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.get(pk=product_id).is_active)


class CartonPricingAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="carton-user",
            email="carton@example.com",
            password="StrongPass123!",
        )
        self.staff = User.objects.create_user(
            username="carton-staff",
            email="carton-staff@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.product = Product.objects.create(
            name="Boxed Product",
            purchase_price=Decimal("50"),
            selling_price=Decimal("75"),
        )
        self.client = APIClient()

    def test_carton_requires_product(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            reverse("products:cartonpricing-list"),
            {"name": "Box", "units_per_carton": 12, "carton_price": "800"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_staff_can_create_carton_pricing_for_active_product(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.post(
            reverse("products:cartonpricing-list"),
            {
                "product": self.product.pk,
                "name": "Box",
                "units_per_carton": 12,
                "carton_price": "800",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["product"], self.product.pk)
        self.assertTrue(CartonPricing.objects.filter(product=self.product).exists())
