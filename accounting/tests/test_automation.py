from decimal import Decimal

from django.test import TestCase

from accounting.models import Account, JournalEntry
from accounting.services import ensure_default_accounts, post_customer_collection, post_purchase, post_sales_invoice
from accounts.models import CustomUserModel
from customers.models import Customer
from invoices.models import Invoice, InvoiceItem
from organization.models import Company
from payments.models import PaymentTransaction
from products.models import Product
from purchases.models import Purchase, PurchaseItem
from suppliers.models import Supplier


class AccountingAutomationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Automation Company")
        self.user = CustomUserModel.objects.create_user(
            username="automation-user",
            email="automation@test.local",
            password="strong-password-123",
        )
        self.customer = Customer.objects.create(name="Customer")
        self.supplier = Supplier.objects.create(name="Supplier")
        self.product = Product.objects.create(name="Widget", purchase_price=Decimal("40.00"), selling_price=Decimal("100.00"))

    def test_sales_posting_creates_ar_revenue_and_cogs(self):
        invoice = Invoice.objects.create(customer=self.customer, created_by=self.user)
        InvoiceItem.objects.create(invoice=invoice, product=self.product, quantity=2, unit_price=Decimal("100.00"), cost_price=Decimal("40.00"))
        entry = post_sales_invoice(invoice=invoice, actor_id=self.user.pk, company=self.company)
        self.assertEqual(entry.status, JournalEntry.Status.POSTED)
        self.assertEqual(entry.lines.count(), 4)
        self.assertEqual(entry.lines.filter(account__code="1200", debit=Decimal("200.00")).count(), 1)
        self.assertEqual(entry.lines.filter(account__code="4100", credit=Decimal("200.00")).count(), 1)
        self.assertEqual(entry.lines.filter(account__code="5100", debit=Decimal("80.00")).count(), 1)
        self.assertEqual(entry.lines.filter(account__code="1100", credit=Decimal("80.00")).count(), 1)
        self.assertEqual(post_sales_invoice(invoice=invoice, actor_id=self.user.pk, company=self.company).pk, entry.pk)

    def test_sales_posting_uses_item_cost_snapshot(self):
        invoice = Invoice.objects.create(customer=self.customer, created_by=self.user)
        InvoiceItem.objects.create(invoice=invoice, product=self.product, quantity=2, unit_price=Decimal("100.00"), cost_price=Decimal("25.00"))
        self.product.purchase_price = Decimal("90.00")
        self.product.save(update_fields=("purchase_price", "updated_at"))
        entry = post_sales_invoice(invoice=invoice, actor_id=self.user.pk, company=self.company)
        self.assertEqual(entry.lines.filter(account__code="5100", debit=Decimal("50.00")).count(), 1)

    def test_purchase_posting_creates_inventory_and_ap(self):
        purchase = Purchase.objects.create(supplier=self.supplier, created_by=self.user)
        PurchaseItem.objects.create(purchase=purchase, product=self.product, quantity=3, unit_purchase_price=Decimal("40.00"))
        entry = post_purchase(purchase=purchase, actor_id=self.user.pk, company=self.company)
        self.assertEqual(entry.status, JournalEntry.Status.POSTED)
        self.assertEqual(entry.lines.filter(account__code="1100", debit=Decimal("120.00")).count(), 1)
        self.assertEqual(entry.lines.filter(account__code="2100", credit=Decimal("120.00")).count(), 1)

    def test_collection_posts_cash_and_ar(self):
        payment = PaymentTransaction.objects.create(customer=self.customer, collected_by=self.user, cash_amount=Decimal("60.00"), transfer_amount=Decimal("0.00"))
        entry = post_customer_collection(payment=payment, actor_id=self.user.pk, company=self.company)
        self.assertEqual(entry.status, JournalEntry.Status.POSTED)
        self.assertEqual(entry.lines.filter(account__code="1010", debit=Decimal("60.00")).count(), 1)
        self.assertEqual(entry.lines.filter(account__code="1200", credit=Decimal("60.00")).count(), 1)

    def test_default_accounts_are_created_once(self):
        first = ensure_default_accounts(self.company)
        second = ensure_default_accounts(self.company)
        self.assertEqual(first["inventory"].pk, second["inventory"].pk)
        self.assertEqual(Account.objects.filter(company=self.company).count(), 9)
