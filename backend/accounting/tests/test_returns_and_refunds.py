from decimal import Decimal

from django.test import TestCase

from accounting.models import JournalEntry
from accounting.services import ensure_default_accounts
from accounting.services.automation import post_payment_refund, post_purchase_return, post_sales_return
from accounts.models import CustomUserModel
from customers.models import Customer
from invoices.models import Invoice, InvoiceItem, InvoiceReturn, InvoiceReturnItem
from organization.models import Company
from payments.models import PaymentAllocation, PaymentRefund, PaymentTransaction
from products.models import Product
from purchases.models import Purchase, PurchaseItem, PurchaseReturn, PurchaseReturnItem
from suppliers.models import Supplier


class AccountingReturnTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Return Company")
        self.user = CustomUserModel.objects.create_user(
            username="returns-user",
            email="returns@test.local",
            password="strong-password-123",
        )
        self.customer = Customer.objects.create(name="Customer")
        self.supplier = Supplier.objects.create(name="Supplier")
        self.product = Product.objects.create(name="Widget", purchase_price=Decimal("40.00"), selling_price=Decimal("100.00"))
        ensure_default_accounts(self.company)

    def test_sales_return_reverses_revenue_and_cogs(self):
        invoice = Invoice.objects.create(customer=self.customer, created_by=self.user)
        item = InvoiceItem.objects.create(invoice=invoice, product=self.product, quantity=2, unit_price=Decimal("100.00"), cost_price=Decimal("40.00"))
        returned = InvoiceReturn.objects.create(invoice=invoice, created_by=self.user, refund_amount=Decimal("100.00"))
        InvoiceReturnItem.objects.create(invoice_return=returned, invoice_item=item, quantity=1, unit_price=Decimal("100.00"))

        entry = post_sales_return(sales_return=returned, actor_id=self.user.pk, company=self.company)
        self.assertEqual(entry.status, JournalEntry.Status.POSTED)
        self.assertEqual(entry.lines.filter(account__code="4200", debit=Decimal("100.00")).count(), 1)
        self.assertEqual(entry.lines.filter(account__code="1200", credit=Decimal("100.00")).count(), 1)
        self.assertEqual(entry.lines.filter(account__code="1100", debit=Decimal("40.00")).count(), 1)
        self.assertEqual(entry.lines.filter(account__code="5100", credit=Decimal("40.00")).count(), 1)
        self.assertEqual(post_sales_return(sales_return=returned, actor_id=self.user.pk, company=self.company).pk, entry.pk)

    def test_purchase_return_reduces_inventory_and_ap(self):
        purchase = Purchase.objects.create(supplier=self.supplier, created_by=self.user, reference="P-1")
        item = PurchaseItem.objects.create(purchase=purchase, product=self.product, quantity=2, unit_purchase_price=Decimal("40.00"))
        returned = PurchaseReturn.objects.create(purchase=purchase, created_by=self.user)
        PurchaseReturnItem.objects.create(purchase_return=returned, purchase_item=item, quantity=1, unit_price=Decimal("40.00"))

        entry = post_purchase_return(purchase_return=returned, actor_id=self.user.pk, company=self.company)
        self.assertEqual(entry.lines.filter(account__code="2100", debit=Decimal("40.00")).count(), 1)
        self.assertEqual(entry.lines.filter(account__code="1100", credit=Decimal("40.00")).count(), 1)

    def test_payment_refund_reopens_ar_against_cash(self):
        invoice = Invoice.objects.create(customer=self.customer, created_by=self.user, status=Invoice.Status.PAID)
        payment = PaymentTransaction.objects.create(customer=self.customer, collected_by=self.user, cash_amount=Decimal("60.00"), transfer_amount=Decimal("0.00"))
        allocation = PaymentAllocation.objects.create(transaction=payment, invoice=invoice, cash_amount=Decimal("60.00"), transfer_amount=Decimal("0.00"))
        refund = PaymentRefund.objects.create(transaction=payment, invoice=invoice, allocation=allocation, cash_amount=Decimal("25.00"), transfer_amount=Decimal("0.00"), created_by=self.user)

        entry = post_payment_refund(refund=refund, actor_id=self.user.pk, company=self.company)
        self.assertEqual(entry.lines.filter(account__code="1200", debit=Decimal("25.00")).count(), 1)
        self.assertEqual(entry.lines.filter(account__code="1010", credit=Decimal("25.00")).count(), 1)
