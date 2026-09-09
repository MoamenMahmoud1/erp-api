from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounting.models import Account, JournalEntry, JournalLine
from accounting.services import (
    customer_aging,
    customer_balances,
    post_customer_collection,
    post_payment_refund,
    post_purchase,
    post_sales_invoice,
    post_supplier_payment,
    supplier_aging,
    supplier_balances,
)
from accounting.services.ledger_balances import owner_ledger_balances
from accounts.models import CustomUserModel
from customers.models import Customer
from invoices.models import Invoice, InvoiceItem
from organization.models import Company
from payments.models import PaymentAllocation, PaymentRefund, PaymentTransaction
from products.models import Product
from purchases.models import Purchase, PurchaseItem, SupplierPayment, SupplierPaymentAllocation
from suppliers.models import Supplier


class BalanceReportTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Balance Reports Company")
        self.user = CustomUserModel.objects.create_user(
            username="balance-reports-user",
            email="balance-reports@test.local",
            password="strong-password-123",
        )
        self.customer = Customer.objects.create(name="Acme Customer")
        self.supplier = Supplier.objects.create(name="Acme Supplier")
        self.product = Product.objects.create(
            name="Test Product",
            purchase_price=Decimal("40"),
            selling_price=Decimal("100"),
        )

    def _invoice(self, customer, *, created_at=None, price="100", quantity=1):
        invoice = Invoice.objects.create(customer=customer, created_by=self.user, status=Invoice.Status.CONFIRMED)
        InvoiceItem.objects.create(invoice=invoice, product=self.product, quantity=quantity, unit_price=Decimal(price))
        if created_at:
            Invoice.objects.filter(pk=invoice.pk).update(created_at=created_at)
            invoice.refresh_from_db()
        return invoice

    def _purchase(self, *, created_at=None, price="200", quantity=1):
        purchase = Purchase.objects.create(supplier=self.supplier, created_by=self.user, status=Purchase.Status.CONFIRMED)
        PurchaseItem.objects.create(
            purchase=purchase,
            product=self.product,
            quantity=quantity,
            unit_purchase_price=Decimal(price),
        )
        if created_at:
            Purchase.objects.filter(pk=purchase.pk).update(created_at=created_at)
            purchase.refresh_from_db()
        return purchase

    def test_customer_balance_accounts_for_collections_and_refunds(self):
        invoice = self._invoice(self.customer)
        post_sales_invoice(invoice=invoice, actor_id=self.user.pk, company=self.company)
        payment = PaymentTransaction.objects.create(
            customer=self.customer,
            collected_by=self.user,
            cash_amount=Decimal("60"),
            transfer_amount=Decimal("0"),
        )
        allocation = PaymentAllocation.objects.create(
            transaction=payment,
            invoice=invoice,
            cash_amount=Decimal("60"),
            transfer_amount=Decimal("0"),
        )
        post_customer_collection(payment=payment, actor_id=self.user.pk, company=self.company)
        refund = PaymentRefund.objects.create(
            transaction=payment,
            invoice=invoice,
            allocation=allocation,
            cash_amount=Decimal("10"),
            transfer_amount=Decimal("0"),
            created_by=self.user,
        )
        post_payment_refund(refund=refund, actor_id=self.user.pk, company=self.company)

        result = customer_balances(as_of=timezone.localdate(), customer_id=self.customer.pk)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["invoiced"], Decimal("100"))
        self.assertEqual(result[0]["paid"], Decimal("60"))
        self.assertEqual(result[0]["refunded"], Decimal("10"))
        self.assertEqual(result[0]["balance"], Decimal("50"))

    def test_supplier_balance_accounts_for_payment(self):
        purchase = self._purchase()
        post_purchase(purchase=purchase, actor_id=self.user.pk, company=self.company)
        payment = SupplierPayment.objects.create(
            supplier=self.supplier,
            paid_by=self.user,
            cash_amount=Decimal("75"),
            transfer_amount=Decimal("0"),
        )
        SupplierPaymentAllocation.objects.create(
            payment=payment,
            purchase=purchase,
            cash_amount=Decimal("75"),
            transfer_amount=Decimal("0"),
        )
        post_supplier_payment(payment=payment, actor_id=self.user.pk, company=self.company)

        result = supplier_balances(as_of=timezone.localdate(), supplier_id=self.supplier.pk)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["purchased"], Decimal("200"))
        self.assertEqual(result[0]["paid"], Decimal("75"))
        self.assertEqual(result[0]["balance"], Decimal("125"))

    def test_owner_ledger_balances_query_count_is_bounded(self):
        account = Account.objects.create(
            company=self.company,
            code="1200",
            name="Accounts Receivable",
            account_type=Account.AccountType.ASSET,
        )
        invoice = self._invoice(self.customer)
        entry = JournalEntry.objects.create(
            company=self.company,
            number=1,
            entry_date=timezone.localdate(),
            source_type="invoice.sale",
            source_id=invoice.pk,
            created_by=self.user,
            status=JournalEntry.Status.POSTED,
        )
        JournalLine.objects.create(
            entry=entry,
            account=account,
            debit=Decimal("100"),
            credit=Decimal("0"),
        )

        with self.assertNumQueries(5):
            result = owner_ledger_balances(
                owner_kind="customer",
                as_of=timezone.localdate(),
                company=self.company,
            )

        self.assertEqual(result[self.customer.pk], Decimal("100"))

    def test_customer_aging_places_open_invoice_in_correct_bucket(self):
        as_of = timezone.localdate()
        invoice = self._invoice(
            self.customer,
            created_at=timezone.now() - timedelta(days=45),
            price="120",
        )
        result = customer_aging(as_of=as_of, customer_id=self.customer.pk)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["0_30"], Decimal("0.00"))
        self.assertEqual(result[0]["31_60"], Decimal("120.00"))
        self.assertEqual(result[0]["61_90"], Decimal("0.00"))
        self.assertEqual(result[0]["90_plus"], Decimal("0.00"))
        self.assertEqual(result[0]["total"], Decimal("120.00"))
        self.assertEqual(invoice.customer_id, self.customer.pk)

    def test_supplier_aging_places_open_purchase_in_90_plus_bucket(self):
        as_of = timezone.localdate()
        purchase = self._purchase(created_at=timezone.now() - timedelta(days=120), price="300")
        result = supplier_aging(as_of=as_of, supplier_id=self.supplier.pk)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["0_30"], Decimal("0.00"))
        self.assertEqual(result[0]["31_60"], Decimal("0.00"))
        self.assertEqual(result[0]["61_90"], Decimal("0.00"))
        self.assertEqual(result[0]["90_plus"], Decimal("300.00"))
        self.assertEqual(result[0]["total"], Decimal("300.00"))
        self.assertEqual(purchase.supplier_id, self.supplier.pk)
