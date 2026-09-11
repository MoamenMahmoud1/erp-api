from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Employee, EmployeeShift, RoleProfile
from auditlog.models import AuditEvent
from customers.models import Customer
from inventory.api.transfer_requests import (
    StockTransferRequestApproveView,
    StockTransferRequestListCreateView,
)
from inventory.api.views import LocationListView, MovementListView, StockBalanceListView, TransferView
from inventory.models import StockBalance, StockLocation, StockTransferRequest
from inventory.services.stock_balance import StockBalanceService
from invoices.models import Invoice, InvoiceItem
from invoices.services import ConfirmInvoice
from organization.models import Company, Site
from payments.services.collection import collect
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

        rep_group = Group.objects.create(name="Sales Representative")
        RoleProfile.objects.create(group=rep_group, name="Sales Representative", level=10, scope=RoleProfile.Scope.SITE, requires_shift=True)
        manager_group = Group.objects.create(name="Warehouse Manager")
        RoleProfile.objects.create(group=manager_group, name="Warehouse Manager", level=20, scope=RoleProfile.Scope.SITE, requires_shift=False)
        self.rep.groups.add(rep_group)
        self.manager.groups.add(manager_group)

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
        self.customer = Customer.objects.create(name="Return Customer")
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

    def _create_approved_paid_invoice_with_return_stock(self):
        invoice = Invoice.objects.create(
            customer=self.customer,
            created_by=self.rep,
            site=self.shift.site,
            shift=self.shift,
            status=Invoice.Status.DRAFT,
        )
        line = InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            quantity=1,
            unit_price=Decimal("100.00"),
        )
        StockBalanceService.increase(
            location=self.vehicle,
            product=self.product,
            quantity=1,
            unit_cost=self.product.purchase_price,
        )
        ConfirmInvoice()(invoice.pk, actor=self.rep)
        collect(
            customer=self.customer,
            cash_amount=Decimal("100.00"),
            transfer_amount=Decimal("0.00"),
            collected_by_id=self.rep.pk,
            actor=self.rep,
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertEqual(StockBalance.objects.get(location=self.vehicle, product=self.product).quantity, 0)
        StockBalanceService.increase(
            location=self.vehicle,
            product=self.product,
            quantity=1,
            unit_cost=self.product.purchase_price,
        )
        return invoice, line

    def _create_loading_request(self):
        request = self.factory.post(
            "/api/v1/inventory/transfer-requests/",
            {
                "request_type": StockTransferRequest.RequestType.WAREHOUSE_TO_VEHICLE,
                "warehouse": self.warehouse.pk,
                "warehouse_manager": self.manager.pk,
                "items": [{"product": self.product.pk, "quantity": 4}],
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="loading-request",
        )
        force_authenticate(request, user=self.rep)
        response = StockTransferRequestListCreateView.as_view()(request)
        self.assertEqual(response.status_code, 201)
        return response

    def test_request_stays_pending_without_moving_stock_and_records_activity(self):
        response = self._create_loading_request()
        request_id = response.data["id"]

        self.assertEqual(response.data["status"], StockTransferRequest.Status.PENDING)
        self.assertEqual(StockBalance.objects.get(location=self.warehouse, product=self.product).quantity, 10)
        self.assertFalse(StockBalance.objects.filter(location=self.vehicle, product=self.product).exists())
        event = AuditEvent.objects.get(entity_type="StockTransferRequest", entity_id=request_id, action="inventory.transfer_request.created")
        self.assertEqual(event.actor_id, self.rep.pk)

    def test_manager_approval_moves_stock_and_records_approver(self):
        created = self._create_loading_request()
        request_id = created.data["id"]

        approve_request = self.factory.post(
            f"/api/v1/inventory/transfer-requests/{request_id}/approve/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY="approve-loading-request",
        )
        force_authenticate(approve_request, user=self.manager)
        response = StockTransferRequestApproveView.as_view()(approve_request, pk=request_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], StockTransferRequest.Status.APPROVED)
        self.assertEqual(StockBalance.objects.get(location=self.warehouse, product=self.product).quantity, 6)
        self.assertEqual(StockBalance.objects.get(location=self.vehicle, product=self.product).quantity, 4)
        event = AuditEvent.objects.get(entity_type="StockTransferRequest", entity_id=request_id, action="inventory.transfer_request.approved")
        self.assertEqual(event.actor_id, self.manager.pk)
        self.assertEqual(event.metadata["requested_by_id"], self.rep.pk)
        self.assertEqual(event.metadata["requester_role_level"], 10)
        self.assertEqual(event.metadata["approver_role_level"], 20)

    def test_same_role_cannot_approve(self):
        peer = get_user_model().objects.create_user(
            username="peer-manager",
            email="peer-manager@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        peer.user_permissions.set(self.manager.user_permissions.all())
        peer_group = Group.objects.create(name="Peer Manager")
        RoleProfile.objects.create(group=peer_group, name="Peer Manager", level=20, scope=RoleProfile.Scope.SITE)
        peer.groups.add(peer_group)
        Employee.objects.create(user=peer, work_site=self.shift.site)
        self.warehouse.warehouse_managers.add(peer)

        created = self._create_loading_request()
        request_id = created.data["id"]
        approve_request = self.factory.post(
            f"/api/v1/inventory/transfer-requests/{request_id}/approve/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY="approve-peer-request",
        )
        force_authenticate(approve_request, user=peer)
        response = StockTransferRequestApproveView.as_view()(approve_request, pk=request_id)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(StockTransferRequest.objects.get(pk=request_id).status, StockTransferRequest.Status.PENDING)

    def test_manager_approval_moves_customer_return_from_vehicle_to_warehouse(self):
        invoice, line = self._create_approved_paid_invoice_with_return_stock()
        create_request = self.factory.post(
            "/api/v1/inventory/transfer-requests/",
            {
                "request_type": StockTransferRequest.RequestType.VEHICLE_TO_WAREHOUSE,
                "warehouse": self.warehouse.pk,
                "warehouse_manager": self.manager.pk,
                "invoice": invoice.pk,
                "items": [{"product": self.product.pk, "quantity": 1, "invoice_item": line.pk}],
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="return-request",
        )
        force_authenticate(create_request, user=self.rep)
        created = StockTransferRequestListCreateView.as_view()(create_request)
        self.assertEqual(created.status_code, 201)
        request_id = created.data["id"]
        self.assertEqual(StockBalance.objects.get(location=self.vehicle, product=self.product).quantity, 1)

        approve_request = self.factory.post(
            f"/api/v1/inventory/transfer-requests/{request_id}/approve/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY="approve-return-request",
        )
        force_authenticate(approve_request, user=self.manager)
        response = StockTransferRequestApproveView.as_view()(approve_request, pk=request_id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], StockTransferRequest.Status.APPROVED)
        self.assertEqual(StockBalance.objects.get(location=self.vehicle, product=self.product).quantity, 0)
        self.assertEqual(StockBalance.objects.get(location=self.warehouse, product=self.product).quantity, 11)
        invoice.refresh_from_db()
        self.assertEqual(invoice.refunded_amount, Decimal("100.00"))
        self.assertEqual(invoice.status, Invoice.Status.RETURNED)
