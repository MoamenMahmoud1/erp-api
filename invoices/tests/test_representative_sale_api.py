from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Employee, EmployeeShift, RoleProfile
from customer_assignments.models import CustomerAssignment
from inventory.models import StockBalance, StockLocation
from invoices.api.views import InvoiceViewSet
from invoices.models import Invoice
from payments.models import PaymentAllocation, PaymentTransaction
from organization.models import Company, Site
from customers.models import Customer
from products.models import Product


class RepresentativeSaleIdempotencyTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.company = Company.objects.create(name="Representative Sale Company")
        self.site = Site.objects.create(
            company=self.company,
            code="REP-SALE",
            name="Representative Sale Branch",
            site_type=Site.Type.BRANCH,
            address_line_1="Test address",
            city="Cairo",
            country_code="EG",
        )

        manager_group = Group.objects.create(name="Representative Sale Manager")
        RoleProfile.objects.create(
            group=manager_group,
            name="Representative Sale Manager",
            level=20,
            scope=RoleProfile.Scope.SITE,
            requires_shift=False,
        )
        rep_group = Group.objects.create(name="Representative Sale Rep")
        RoleProfile.objects.create(
            group=rep_group,
            name="Representative Sale Rep",
            level=10,
            scope=RoleProfile.Scope.SITE,
            requires_shift=True,
        )

        self.manager = User.objects.create_user(
            username="rep-sale-manager",
            email="rep-sale-manager@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.manager.groups.add(manager_group)
        manager_employee = Employee.objects.create(user=self.manager, work_site=self.site)

        self.rep = User.objects.create_user(
            username="rep-sale-rep",
            email="rep-sale-rep@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.rep.groups.add(rep_group)
        Employee.objects.create(
            user=self.rep,
            work_site=self.site,
            manager=manager_employee,
        )

        invoice_permissions = Permission.objects.filter(
            content_type__app_label="invoices",
            codename__in=("add_invoice", "confirm_invoice"),
        )
        self.rep.user_permissions.set(invoice_permissions)
        payment_permission = Permission.objects.get(
            content_type__app_label="payments",
            codename="process_collection",
        )
        self.rep.user_permissions.add(payment_permission)

        self.customer = Customer.objects.create(name="Representative Sale Customer")
        CustomerAssignment.objects.create(customer=self.customer, employee=self.rep.employee)
        self.unassigned_customer = Customer.objects.create(name="Unassigned Customer")
        self.product = Product.objects.create(
            name="Representative Sale Product",
            purchase_price=Decimal("50.00"),
            selling_price=Decimal("100.00"),
        )
        self.vehicle = StockLocation.objects.create(
            name="Representative Sale Vehicle",
            location_type=StockLocation.LocationType.SALES_VEHICLE,
            employee=self.rep,
            site=self.site,
        )
        self.shift = EmployeeShift.objects.create(
            employee=self.rep.employee,
            site=self.site,
            vehicle=self.vehicle,
            business_date="2026-09-10",
            status=EmployeeShift.Status.OPEN,
            opening_cash="0.00",
        )
        StockBalance.objects.create(
            location=self.vehicle,
            product=self.product,
            quantity=5,
            total_cost=Decimal("250.00"),
        )
        self.factory = APIRequestFactory()

    def _request(self, key, body):
        request = self.factory.post(
            "/api/v1/invoices/representative-sale/",
            body,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        force_authenticate(request, user=self.rep)
        return InvoiceViewSet.as_view({"post": "representative_sale"})(request)

    def test_same_key_returns_same_sale_without_duplicate_side_effects(self):
        body = {
            "customer": self.customer.pk,
            "items": [{"product": self.product.pk, "quantity": 2}],
            "payment_method": "cash",
            "payment_amount": "200.00",
        }

        first = self._request("rep-sale-timeout-1", body)
        self.assertEqual(first.status_code, 201)
        invoice_id = first.data["invoice"]["id"]

        second = self._request("rep-sale-timeout-1", body)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data["invoice"]["id"], invoice_id)

        self.assertEqual(Invoice.objects.filter(pk=invoice_id).count(), 1)
        self.assertEqual(PaymentTransaction.objects.filter(customer=self.customer).count(), 1)
        self.assertEqual(PaymentAllocation.objects.filter(invoice_id=invoice_id).count(), 1)
        self.assertEqual(
            StockBalance.objects.get(location=self.vehicle, product=self.product).quantity,
            3,
        )

    def test_same_key_with_different_payload_is_rejected(self):
        key = "rep-sale-conflict-1"
        first_body = {
            "customer": self.customer.pk,
            "items": [{"product": self.product.pk, "quantity": 1}],
            "payment_method": "cash",
            "payment_amount": "100.00",
        }
        conflicting_body = {
            **first_body,
            "items": [{"product": self.product.pk, "quantity": 2}],
        }

        first = self._request(key, first_body)
        self.assertEqual(first.status_code, 201)
        second = self._request(key, conflicting_body)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.data["code"], "idempotency_conflict")

        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_unassigned_customer_is_rejected_without_side_effects(self):
        body = {
            "customer": self.unassigned_customer.pk,
            "items": [{"product": self.product.pk, "quantity": 1}],
            "payment_method": "cash",
            "payment_amount": "100.00",
        }

        response = self._request("rep-sale-unassigned-1", body)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "sale_invalid")
        self.assertIn("not assigned", response.data["detail"].lower())
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertEqual(PaymentTransaction.objects.count(), 0)
        self.assertEqual(
            StockBalance.objects.get(location=self.vehicle, product=self.product).quantity,
            5,
        )
