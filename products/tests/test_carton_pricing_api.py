from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from products.models import CartonPricing, Product


class CartonPricingAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
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
        self.client.force_authenticate(user=self.staff)

    def test_carton_requires_product(self):
        response = self.client.post(
            reverse("products:cartonpricing-list"),
            {"name": "Box", "units_per_carton": 12, "carton_price": "800"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_staff_can_create_carton_pricing_for_active_product(self):
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
