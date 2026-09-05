from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from inventory.api.views import LocationListView, MovementListView, StockBalanceListView, TransferView
from inventory.models import StockBalance

from .helpers import InventoryTestMixin


class InventoryAPITests(InventoryTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()

    def test_locations_are_readable(self):
        request = self.factory.get("/api/v1/inventory/locations/")
        force_authenticate(request, user=self.user)
        response = LocationListView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_stock_filter_by_product(self):
        StockBalance.objects.create(location=self.warehouse, product=self.product, quantity=7)
        request = self.factory.get(f"/api/v1/inventory/stock/?product={self.product.pk}")
        force_authenticate(request, user=self.user)
        response = StockBalanceListView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_transfer_endpoint(self):
        StockBalance.objects.create(location=self.warehouse, product=self.product, quantity=5)
        request = self.factory.post(
            "/api/v1/inventory/transfers/",
            {
                "source_location": self.warehouse.pk,
                "destination_location": self.vehicle.pk,
                "items": [{"product": self.product.pk, "quantity": 2}],
            },
            format="json",
        )
        force_authenticate(request, user=self.user)
        response = TransferView.as_view()(request)
        self.assertEqual(response.status_code, 201)

    def test_movement_endpoint(self):
        request = self.factory.get("/api/v1/inventory/movements/")
        force_authenticate(request, user=self.user)
        response = MovementListView.as_view()(request)
        self.assertEqual(response.status_code, 200)
