from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from invoices.models import Invoice, InvoiceItem
from .helpers import InvoiceTestMixin


class InvoiceScopeTests(InvoiceTestMixin, TestCase):
    def test_actor_sees_own_invoice(self):
        invoice = Invoice.objects.create(customer=self.customer, created_by=self.user)
        self.assertIn(invoice, Invoice.objects.visible_to(self.user))

    def test_actor_cannot_see_other_user_invoice(self):
        other = get_user_model().objects.create_user(
            username="other-invoice",
            email="other-invoice@example.com",
            password="StrongPass123!",
        )
        other_invoice = Invoice.objects.create(customer=self.customer, created_by=other)
        self.assertNotIn(other_invoice, Invoice.objects.visible_to(self.user))

    def test_superuser_sees_all_invoices(self):
        other = get_user_model().objects.create_superuser(
            username="super-invoice",
            email="super-invoice@example.com",
            password="StrongPass123!",
        )
        invoice = Invoice.objects.create(customer=self.customer, created_by=self.user)
        self.assertIn(invoice, Invoice.objects.visible_to(other))
