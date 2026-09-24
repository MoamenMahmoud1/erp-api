from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounting.models import Account, JournalEntry, JournalLine
from accounting.services.ledger_balances import owner_ledger_balances
from accounting.services.reconciliation import reconcile_subledgers
from customers.models import Customer
from invoices.models import Invoice, InvoiceItem
from organization.models import Company
from products.models import Product
from accounts.models import CustomUserModel


class LedgerBalanceReconciliationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company", singleton_marker=True)
        self.user = CustomUserModel.objects.create_user(username="tester", email="tester@example.com", password="pass")
        self.customer = Customer.objects.create(name="Customer")
        self.product = Product.objects.create(name="Product", purchase_price=Decimal("10.00"), selling_price=Decimal("20.00"))
        self.ar = Account.objects.create(company=self.company, code="1200", name="AR", account_type=Account.AccountType.ASSET)
        self.revenue = Account.objects.create(company=self.company, code="4100", name="Revenue", account_type=Account.AccountType.REVENUE)

    def test_ledger_balance_honors_as_of_date(self):
        invoice = Invoice.objects.create(customer=self.customer, created_by=self.user)
        InvoiceItem.objects.create(invoice=invoice, product=self.product, quantity=1, unit_price=Decimal("20.00"))
        early = JournalEntry.objects.create(company=self.company, number=1, entry_date=date(2026, 9, 1), source_type="invoice.sale", source_id=invoice.pk, created_by=self.user, status=JournalEntry.Status.POSTED)
        JournalLine.objects.create(entry=early, account=self.ar, debit=Decimal("20.00"), credit=Decimal("0.00"))
        JournalLine.objects.create(entry=early, account=self.revenue, debit=Decimal("0.00"), credit=Decimal("20.00"))
        late = JournalEntry.objects.create(company=self.company, number=2, entry_date=date(2026, 9, 2), source_type="invoice.sale", source_id=invoice.pk + 1000, created_by=self.user, status=JournalEntry.Status.POSTED)
        JournalLine.objects.create(entry=late, account=self.ar, debit=Decimal("10.00"), credit=Decimal("0.00"))
        JournalLine.objects.create(entry=late, account=self.revenue, debit=Decimal("0.00"), credit=Decimal("10.00"))
        self.assertEqual(owner_ledger_balances(owner_kind="customer", as_of=date(2026, 9, 1))[self.customer.pk], Decimal("20.00"))
