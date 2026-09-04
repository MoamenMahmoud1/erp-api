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
        self.client = APIClient()

    def test_list_and_detail(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("products:product-list"))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse(
                "products:product-detail",
                kwargs={"pk": self.product.pk},
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_cannot_create_update_or_delete(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("products:product-list")
        response = self.client.post(
            url,
            {
                "name": "New Product",
                "purchase_price": "200.00",
                "selling_price": "300.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

        detail_url = reverse(
            "products:product-detail",
            kwargs={"pk": self.product.pk},
        )
        response = self.client.patch(
            detail_url,
            {"selling_price": "175.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 403)

    def test_staff_can_create_update_and_delete(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post(
            reverse("products:product-list"),
            {
                "name": "New Product",
                "purchase_price": "200.00",
                "selling_price": "300.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        product_id = response.data["id"]

        detail_url = reverse(
            "products:product-detail",
            kwargs={"pk": product_id},
        )
        response = self.client.patch(
            detail_url,
            {"selling_price": "175.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.selling_price, Decimal("175.00"))

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Product.objects.filter(pk=product_id).exists())


class CartonPricingAPITests(TestCase):
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
        self.client = APIClient()

    def test_list_and_detail(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("products:cartonpricing-list"))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse(
                "products:cartonpricing-detail",
                kwargs={"pk": self.carton.pk},
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_regular_user_cannot_write(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("products:cartonpricing-list"),
            {
                "name": "Large Box",
                "units_per_carton": 24,
                "carton_price": "1800.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_can_create_update_delete(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post(
            reverse("products:cartonpricing-list"),
            {
                "name": "Large Box",
                "units_per_carton": 24,
                "carton_price": "1800.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        carton_id = response.data["id"]

        detail_url = reverse(
            "products:cartonpricing-detail",
            kwargs={"pk": carton_id},
        )
        response = self.client.patch(
            detail_url,
            {"carton_price": "1200.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(CartonPricing.objects.filter(pk=carton_id).exists())
