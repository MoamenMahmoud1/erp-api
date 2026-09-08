from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from inventory.api.views import (
    LocationListView,
    MovementListView,
    StockBalanceListView,
    TransferView,
)
from inventory.permissions import InventoryReadPermission, InventoryTransferPermission


class InventoryPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="inventory-permission-user",
            email="inventory-permission@example.com",
            password="StrongPass123!",
        )
        self.factory = APIRequestFactory()

    def _grant(self, codename):
        permission = Permission.objects.get(
            content_type__app_label="inventory",
            codename=codename,
        )
        self.user.user_permissions.add(permission)
        for cache_name in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache_name, None)

    def _request(self, method, path, view):
        request = getattr(self.factory, method)(path)
        request.user = self.user
        return request, view

    def test_unauthenticated_inventory_read_is_denied(self):
        request = self.factory.get("/api/v1/inventory/stock/")
        request.user = None
        self.assertFalse(InventoryReadPermission().has_permission(request, StockBalanceListView()))

    def test_request_without_user_attribute_is_denied(self):
        request = self.factory.get("/api/v1/inventory/stock/")
        self.assertFalse(InventoryReadPermission().has_permission(request, StockBalanceListView()))
        self.assertFalse(InventoryTransferPermission().has_permission(request, TransferView()))

    def test_location_read_requires_explicit_permission(self):
        request, view = self._request("get", "/api/v1/inventory/locations/", LocationListView())
        self.assertFalse(InventoryReadPermission().has_permission(request, view))
        self._grant("view_stocklocation")
        self.assertTrue(InventoryReadPermission().has_permission(request, view))

    def test_stock_read_requires_explicit_permission(self):
        request, view = self._request("get", "/api/v1/inventory/stock/", StockBalanceListView())
        self.assertFalse(InventoryReadPermission().has_permission(request, view))
        self._grant("view_stockbalance")
        self.assertTrue(InventoryReadPermission().has_permission(request, view))

    def test_movement_read_requires_explicit_permission(self):
        request, view = self._request("get", "/api/v1/inventory/movements/", MovementListView())
        self.assertFalse(InventoryReadPermission().has_permission(request, view))
        self._grant("view_stockmovement")
        self.assertTrue(InventoryReadPermission().has_permission(request, view))

    def test_transfer_requires_explicit_transfer_permission(self):
        request, view = self._request("post", "/api/v1/inventory/transfers/", TransferView())
        self.assertFalse(InventoryTransferPermission().has_permission(request, view))
        self._grant("transfer_stock")
        self.assertTrue(InventoryTransferPermission().has_permission(request, view))
