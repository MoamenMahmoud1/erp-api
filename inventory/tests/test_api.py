from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Employee, EmployeeShift
from inventory.api.transfer_requests import (
    StockTransferRequestApproveView,
    StockTransferRequestListCreateView,
)
from inventory.api.views import LocationListView, MovementListView, StockBalanceListView, TransferView
from inventory.models import StockBalance, StockLocation, StockTransferRequest
from organization.models import Company, Site
from products.models import Product

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

    def test_direct_transfer_is_not_available_to_requesting_representative(self):
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
        self.assertEqual(response.status_code, 403)
        self.assertEqual(StockBalance.objects.get(location=self.warehouse, product=self.product).quantity, 5)

    def test_movement_endpoint(self):
        request = self.factory.get("/api/v1/inventory/movements/")
        force_authenticate(request, user=self.user)
        response = MovementListView.as_view()(request)
        self.assertEqual(response.status_code, 200)


class StockTransferRequestAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.rep = User.objects.create_user(
            username="rep-user",
            email="rep@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.manager = User.objects.create_user(
            username="warehouse-manager",
            email="manager@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        permissions = Permission.objects.filter(
            content_type__app_label="inventory",
            codename__in=(
                "transfer_stock",
                "approve_stock_transfer",
                "view_stocklocation",
                "view_stockbalance",
            ),
        )
        self.rep.user_permissions.set(permissions.filter(codename__in=("transfer_stock", "view_stocklocation", "view_stockbalance")))
        self.manager.user_permissions.set(permissions)

        company = Company.objects.create(name="Transfer Request Company")
        site = Site.objects.create(
            company=company,
            code="TR-ST",
            name="Transfer Request Branch",
            site_type=Site.Type.BRANCH,
            address_line_1="Test address",
            city="Cairo",
            country_code="EG",
        )
        Employee.objects.create(user=self.rep, work_site=site)
        Employee.objects.create(user=self.manager, work_site=site)
        self.product = Product.objects.create(
            name="Approved Widget",
            purchase_price="50.00",
            selling_price="100.00",
        )
        self.warehouse = StockLocation.objects.create(
            name="Request Warehouse",
            location_type=StockLocation.LocationType.MAIN_WAREHOUSE,
            site=site,
        )
        self.vehicle = StockLocation.objects.create(
            name="Rep Van",
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            employee=self.rep,
            site=site,
        )
        self.warehouse.warehouse_managers.add(self.manager)
        self.shift = EmployeeShift.objects.create(
            employee=self.rep.employee,
            site=site,
            vehicle=self.vehicle,
            business_date=timezone.localdate(),
            status=EmployeeShift.Status.OPEN,
            opening_cash="0.00",
        )
        StockBalance.objects.create(location=self.warehouse, product=self.product, quantity=10)
        self.factory = APIRequestFactory()

    def test_request_stays_pending_without_moving_stock(self):
        request = self.factory.post(
            "/api/v1/inventory/transfer-requests/",
            {
                "request_type": StockTransferRequest.RequestType.WAREHOUSE_TO_VEHICLE,
                "warehouse": self.warehouse.pk,
                "warehouse_manager": self.manager.pk,
                "items": [{"product": self.product.pk, "quantity": 4}],
            },
            format="json",
        )
        force_authenticate(request, user=self.rep)
        response = StockTransferRequestListCreateView.as_view()(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], StockTransferRequest.Status.PENDING)
        self.assertEqual(StockBalance.objects.get(location=self.warehouse, product=self.product).quantity, 10)
        self.assertFalse(StockBalance.objects.filter(location=self.vehicle, product=self.product).exists())

    def test_manager_approval_moves_stock_and_marks_request_approved(self):
        create_request = self.factory.post(
            "/api/v1/inventory/transfer-requests/",
            {
                "request_type": StockTransferRequest.RequestType.WAREHOUSE_TO_VEHICLE,
                "warehouse": self.warehouse.pk,
                "warehouse_manager": self.manager.pk,
                "items": [{"product": self.product.pk, "quantity": 4}],
            },
            format="json",
        )
        force_authenticate(create_request, user=self.rep)
        created = StockTransferRequestListCreateView.as_view()(create_request)
        request_id = created.data["id"]

        approve_request = self.factory.post(f"/api/v1/inventory/transfer-requests/{request_id}/approve/", {}, format="json")
        force_authenticate(approve_request, user=self.manager)
        response = StockTransferRequestApproveView.as_view()(approve_request, pk=request_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], StockTransferRequest.Status.APPROVED)
        self.assertEqual(StockBalance.objects.get(location=self.warehouse, product=self.product).quantity, 6)
        self.assertEqual(StockBalance.objects.get(location=self.vehicle, product=self.product).quantity, 4)
