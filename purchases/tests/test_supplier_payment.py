from decimal import Decimal

from django.test import TestCase

from accounting.models import JournalEntry
from accounting.services import ensure_default_accounts, post_purchase
from accounts.models import CustomUserModel
from organization.models import Company
from products.models import Product
from purchases.models import Purchase, PurchaseItem, PurchaseReturn, PurchaseReturnItem
from purchases.services.supplier_payment import SupplierPaymentOverpaymentError, pay_supplier
from suppliers.models import Supplier


class SupplierPaymentTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Supplier Payment Company")
        self.user = CustomUserModel.objects.create_user(
            email="supplier-payment@test.local", password="strong-password-123"
        )
        self.supplier = Supplier.objects.create(name="Supplier")
        self.product = Product.objects.create(
            name="Widget",
            purchase_price=Decimal("40.00"),
            selling_price=Decimal("100.00"),
        )
        ensure_default_accounts(self.company)

    def _purchase(self, amount, reference):
        purchase = Purchase.objects.create(
            supplier=self.supplier,
            created_by=self.user,
            status=Purchase.Status.CONFIRMED,
            reference=reference,
        )
        PurchaseItem.objects.create(
            purchase=purchase,
            product=self.product,
            quantity=1,
            unit_purchase_price=amount,
        )
        post_purchase(purchase=purchase, actor_id=self.user.pk, company=self.company)
        return purchase

    def test_supplier_payment_allocates_fifo_and_posts_ap(self):
        first = self._purchase(Decimal("100.00"), "P-1")
        second = self._purchase(Decimal("120.00"), "P-2")

        payment = pay_supplier(
            supplier=self.supplier,
            cash_amount=Decimal("150.00"),
            transfer_amount=Decimal("0"),
            paid_by_id=self.user.pk,
        )

        allocations = list(payment.allocations.order_by("created_at", "id"))
        self.assertEqual(len(allocations), 2)
        self.assertEqual(allocations[0].purchase_id, first.pk)
        self.assertEqual(allocations[0].total_amount, Decimal("100.00"))
        self.assertEqual(allocations[1].purchase_id, second.pk)
        self.assertEqual(allocations[1].total_amount, Decimal("50.00"))

        entry = JournalEntry.objects.get(
            source_type="payment.supplier",
            source_id=payment.pk,
            company=self.company,
        )
        self.assertEqual(entry.status, JournalEntry.Status.POSTED)
        self.assertEqual(
            entry.lines.filter(account__code="2100", debit=Decimal("150.00")).count(), 1
        )
        self.assertEqual(
            entry.lines.filter(account__code="1010", credit=Decimal("150.00")).count(), 1
        )

    def test_supplier_payment_accounts_for_purchase_returns(self):
        purchase = self._purchase(Decimal("200.00"), "P-1")
        item = purchase.items.get()
        returned = PurchaseReturn.objects.create(purchase=purchase, created_by=self.user)
        PurchaseReturnItem.objects.create(
            purchase_return=returned,
            purchase_item=item,
            quantity=1,
            unit_price=Decimal("40.00"),
        )

        payment = pay_supplier(
            supplier=self.supplier,
            cash_amount=Decimal("160.00"),
            transfer_amount=Decimal("0"),
            paid_by_id=self.user.pk,
        )
        self.assertEqual(payment.total_amount, Decimal("160.00"))
        self.assertEqual(payment.allocations.get().purchase_id, purchase.pk)

    def test_supplier_payment_rejects_overpayment(self):
        self._purchase(Decimal("100.00"), "P-1")
        with self.assertRaises(SupplierPaymentOverpaymentError):
            pay_supplier(
                supplier=self.supplier,
                cash_amount=Decimal("100.01"),
                transfer_amount=Decimal("0"),
                paid_by_id=self.user.pk,
            )
