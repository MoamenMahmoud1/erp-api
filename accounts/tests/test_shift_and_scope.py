from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from accounts.models import Employee, EmployeeShift, GroupPolicy
from accounts.services.employee_shift import ShiftError, start_shift
from customers.models import Customer
from invoices.models import Invoice, InvoiceItem
from organization.models import Company, Site
from products.models import Product


User = get_user_model()


class EmployeeShiftTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.branch = Site.objects.create(
            company=self.company,
            code="BR-01",
            name="Branch 1",
            site_type=Site.Type.BRANCH,
            address_line_1="Address",
            city="Cairo",
            country_code="EG",
        )
        self.user = User.objects.create_user(username="shop-user", email="shop@test.com", password="StrongPass123!")
        group = Group.objects.create(name="Test Shop Manager")
        GroupPolicy.objects.create(group=group, level=50, scope=GroupPolicy.Scope.SITE, requires_shift=True)
        self.user.groups.add(group)
        self.employee = Employee.objects.create(user=self.user, work_site=self.branch)

    def test_shift_requires_employee_site(self):
        Employee.objects.filter(pk=self.employee.pk).update(work_site=None)
        with self.assertRaises(ShiftError):
            start_shift(user=self.user)

    def test_start_shift_is_bound_to_employee_site(self):
        shift = start_shift(user=self.user, opening_cash=Decimal("100.00"))
        self.assertEqual(shift.site_id, self.branch.pk)
        self.assertEqual(shift.employee_id, self.employee.pk)
        self.assertEqual(shift.status, EmployeeShift.Status.OPEN)

    def test_only_one_shift_per_employee_per_day(self):
        start_shift(user=self.user)
        with self.assertRaises(ShiftError):
            start_shift(user=self.user)

    def test_required_shift_blocks_invoice_creation_context(self):
        product = Product.objects.create(name="Product", purchase_price=Decimal("10"), selling_price=Decimal("20"))
        customer = Customer.objects.create(name="Customer")
        from invoices.services.create import CreateInvoice

        with self.assertRaises(ShiftError):
            CreateInvoice()(created_by=self.user, validated_data={"customer": customer, "items": [{"product": product, "quantity": 1}]})

    def test_invoice_creation_uses_current_shift_context(self):
        shift = start_shift(user=self.user)
        product = Product.objects.create(name="Product", purchase_price=Decimal("10"), selling_price=Decimal("20"))
        customer = Customer.objects.create(name="Customer")
        from invoices.services.create import CreateInvoice

        invoice = CreateInvoice()(created_by=self.user, validated_data={"customer": customer, "items": [{"product": product, "quantity": 1}]})
        self.assertEqual(invoice.site_id, self.branch.pk)
        self.assertEqual(invoice.shift_id, shift.pk)


class SiteScopeTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.branch_a = Site.objects.create(company=self.company, code="BR-A", name="Branch A", site_type=Site.Type.BRANCH, address_line_1="Address", city="Cairo", country_code="EG")
        self.store_a = Site.objects.create(company=self.company, code="ST-A", name="Store A", site_type=Site.Type.STORE, parent=self.branch_a, address_line_1="Address", city="Cairo", country_code="EG")
        self.branch_b = Site.objects.create(company=self.company, code="BR-B", name="Branch B", site_type=Site.Type.BRANCH, address_line_1="Address", city="Cairo", country_code="EG")
        self.user = User.objects.create_user(username="branch-user", email="branch@test.com", password="StrongPass123!")
        group = Group.objects.create(name="Test Branch Manager")
        GroupPolicy.objects.create(group=group, level=60, scope=GroupPolicy.Scope.BRANCH)
        self.user.groups.add(group)
        Employee.objects.create(user=self.user, work_site=self.branch_a)
        customer = Customer.objects.create(name="Customer")
        self.invoice_a = Invoice.objects.create(customer=customer, site=self.store_a, created_by=self.user)
        self.invoice_b = Invoice.objects.create(customer=customer, site=self.branch_b, created_by=self.user)
        InvoiceItem.objects.create(invoice=self.invoice_a, product=Product.objects.create(name="A", purchase_price=Decimal("1"), selling_price=Decimal("2")), quantity=1, unit_price=Decimal("2"))
        InvoiceItem.objects.create(invoice=self.invoice_b, product=Product.objects.create(name="B", purchase_price=Decimal("1"), selling_price=Decimal("2")), quantity=1, unit_price=Decimal("2"))

    def test_branch_manager_sees_branch_and_store_but_not_other_branch(self):
        visible = set(Invoice.objects.visible_to(self.user).values_list("site_id", flat=True))
        self.assertEqual(visible, {self.store_a.pk})
