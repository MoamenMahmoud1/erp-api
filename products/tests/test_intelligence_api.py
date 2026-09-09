from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import CustomUserModel
from products.models import Product


class ProductIntelligenceAPITests(TestCase):
    def setUp(self):
        self.user = CustomUserModel.objects.create_user(
            username="intelligence-api-user",
            email="intelligence-api@test.local",
            password="strong-password-123",
        )
        self.user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="products",
                codename="view_product",
            )
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.product = Product.objects.create(
            name="API Charger",
            purchase_price=Decimal("40.00"),
            selling_price=Decimal("100.00"),
        )

    def test_product_intelligence_returns_live_analysis(self):
        response = self.client.get("/api/v1/products/intelligence/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["product_count"], 1)
        self.assertEqual(response.data["products"][0]["product_id"], self.product.pk)

    def test_product_intelligence_rejects_future_as_of(self):
        future = timezone.localdate() + timedelta(days=1)
        response = self.client.get(
            "/api/v1/products/intelligence/",
            {"as_of": future.isoformat()},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "as_of must not be in the future.")
