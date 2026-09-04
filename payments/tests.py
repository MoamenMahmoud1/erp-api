import asyncio
import threading
from decimal import Decimal

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase
from django.test.client import AsyncRequestFactory
from rest_framework.test import force_authenticate

from common.exceptions import InvalidMoney
from customers.models import Customer
from invoices.models import Invoice, InvoiceItem
from payments.api.views import CollectionView, TransactionListView
from payments.models import IdempotencyKey, PaymentAllocation, PaymentTransaction
from payments.services import (
    NoConfirmableInvoicesError,
    OverpaymentError,
    ProcessCollectionIdempotent,
    _process_collection_sync,
)
from products.models import Product


class PaymentTestMixin:
    def create_user(self, username="cashier", staff=True):
        User = get_user_model()
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="StrongPass123!",
            is_staff=staff,
        )

    def create_product(self, name="Widget", selling_price="100.00"):
        return Product.objects.create(
            name=name,
            purchase_price=Decimal("50.00"),
            selling_price=Decimal(selling_price),
        )

    def create_invoice(
        self,
        customer,
        user,
        product,
        quantity=1,
        unit_price="100.00",
        status=Invoice.Status.CONFIRMED,
    ):
        invoice = Invoice.objects.create(
            customer=customer,
            created_by=user,
            status=status,
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            product=product,
            quantity=quantity,
            unit_price=Decimal(unit_price),
        )
        return invoice


class ProcessCollectionTests(PaymentTestMixin, TransactionTestCase):
    def setUp(self):
        self.user = self.create_user()
        self.customer = Customer.objects.create(name="Acme")
        self.product = self.create_product()

    def collect(self, cash, transfer, collected_by_id=None):
        if collected_by_id is None:
            collected_by_id = self.user.pk
        return _process_collection_sync(
            customer=self.customer,
            cash_amount=Decimal(cash),
            transfer_amount=Decimal(transfer),
            collected_by_id=collected_by_id,
        )

    def test_full_cash_payment_marks_invoice_paid(self):
        invoice = self.create_invoice(self.customer, self.user, self.product, quantity=1)
        tx = self.collect("100.00", "0.00")
        self.assertIsNotNone(tx)
        self.assertEqual(tx.cash_amount, Decimal("100.00"))
        alloc = PaymentAllocation.objects.get(transaction=tx, invoice=invoice)
        self.assertEqual(alloc.cash_amount, Decimal("100.00"))
        self.assertEqual(alloc.transfer_amount, Decimal("0.00"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)

    def test_full_transfer_payment(self):
        invoice = self.create_invoice(self.customer, self.user, self.product, quantity=1)
        tx = self.collect("0.00", "100.00")
        alloc = PaymentAllocation.objects.get(transaction=tx, invoice=invoice)
        self.assertEqual(alloc.cash_amount, Decimal("0.00"))
        self.assertEqual(alloc.transfer_amount, Decimal("100.00"))

    def test_mixed_cash_and_transfer(self):
        invoice = self.create_invoice(self.customer, self.user, self.product, quantity=1)
        tx = self.collect("60.00", "40.00")
        alloc = PaymentAllocation.objects.get(transaction=tx, invoice=invoice)
        self.assertEqual(alloc.cash_amount, Decimal("60.00"))
        self.assertEqual(alloc.transfer_amount, Decimal("40.00"))
        self.assertEqual(tx.total_amount, Decimal("100.00"))

    def test_partial_payment_leaves_invoice_confirmed(self):
        invoice = self.create_invoice(self.customer, self.user, self.product, quantity=1)
        tx = self.collect("30.00", "0.00")
        alloc = PaymentAllocation.objects.get(transaction=tx)
        self.assertEqual(alloc.total_amount, Decimal("30.00"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.CONFIRMED)
        self.assertEqual(invoice.paid_amount, Decimal("30.00"))
        self.assertEqual(invoice.outstanding_amount, Decimal("70.00"))

    def test_multi_invoice_oldest_first_cash_then_transfer(self):
        old = self.create_invoice(self.customer, self.user, self.product, quantity=1)
        new = self.create_invoice(self.customer, self.user, self.product, quantity=1)
        self.assertLess(old.pk, new.pk)
        tx = self.collect("80.00", "120.00")
        old_alloc = PaymentAllocation.objects.get(transaction=tx, invoice=old)
        new_alloc = PaymentAllocation.objects.get(transaction=tx, invoice=new)
        self.assertEqual(old_alloc.cash_amount, Decimal("80.00"))
        self.assertEqual(old_alloc.transfer_amount, Decimal("20.00"))
        self.assertEqual(new_alloc.cash_amount, Decimal("0.00"))
        self.assertEqual(new_alloc.transfer_amount, Decimal("100.00"))
        old.refresh_from_db()
        new.refresh_from_db()
        self.assertEqual(old.status, Invoice.Status.PAID)
        self.assertEqual(new.status, Invoice.Status.PAID)

    def test_oldest_invoice_paid_first(self):
        old = self.create_invoice(self.customer, self.user, self.product, quantity=1)
        new = self.create_invoice(
            self.customer, self.user, self.product, quantity=1, unit_price="50.00"
        )
        tx = self.collect("120.00", "0.00")
        old_alloc = PaymentAllocation.objects.get(transaction=tx, invoice=old)
        new_alloc = PaymentAllocation.objects.get(transaction=tx, invoice=new)
        self.assertEqual(old_alloc.total_amount, Decimal("100.00"))
        self.assertEqual(new_alloc.total_amount, Decimal("20.00"))
        old.refresh_from_db()
        new.refresh_from_db()
        self.assertEqual(old.status, Invoice.Status.PAID)
        self.assertEqual(new.status, Invoice.Status.CONFIRMED)

    def test_exact_payment_across_invoices(self):
        self.create_invoice(self.customer, self.user, self.product, quantity=1)
        self.create_invoice(self.customer, self.user, self.product, quantity=1)
        tx = self.collect("100.00", "100.00")
        self.assertEqual(PaymentAllocation.objects.filter(transaction=tx).count(), 2)

    def test_overpayment_is_rejected(self):
        self.create_invoice(self.customer, self.user, self.product, quantity=1)
        with self.assertRaises(OverpaymentError):
            self.collect("150.00", "0.00")
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_negative_amounts_are_rejected(self):
        self.create_invoice(self.customer, self.user, self.product, quantity=1)
        with self.assertRaises(InvalidMoney):
            self.collect("-1.00", "0.00")
        with self.assertRaises(InvalidMoney):
            self.collect("0.00", "-5.00")

    def test_zero_collection_is_a_noop(self):
        self.create_invoice(self.customer, self.user, self.product, quantity=1)
        result = self.collect("0.00", "0.00")
        self.assertIsNone(result)
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_draft_and_cancelled_invoices_are_not_collectible(self):
        self.create_invoice(
            self.customer, self.user, self.product, status=Invoice.Status.DRAFT
        )
        self.create_invoice(
            self.customer, self.user, self.product, status=Invoice.Status.CANCELLED
        )
        with self.assertRaises(NoConfirmableInvoicesError):
            self.collect("10.00", "0.00")
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_rollback_on_failed_allocation(self):
        self.create_invoice(self.customer, self.user, self.product, quantity=1)
        with self.assertRaises(OverpaymentError):
            self.collect("9999.00", "0.00")
        self.assertFalse(PaymentTransaction.objects.exists())
        self.assertFalse(PaymentAllocation.objects.exists())

    def test_allocation_uniqueness_constraint(self):
        invoice = self.create_invoice(self.customer, self.user, self.product, quantity=1)
        tx = self.collect("100.00", "0.00")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PaymentAllocation.objects.create(
                    transaction=tx,
                    invoice=invoice,
                    cash_amount=Decimal("1.00"),
                    transfer_amount=Decimal("0.00"),
                )

    def test_cumulative_payments_transition_to_paid(self):
        invoice = self.create_invoice(self.customer, self.user, self.product, quantity=1)
        self.collect("70.00", "0.00")
        self.collect("30.00", "0.00")
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertEqual(invoice.paid_amount, Decimal("100.00"))

    def test_concurrent_collections_cannot_double_allocate(self):
        invoice = self.create_invoice(self.customer, self.user, self.product, quantity=1)
        results = []
        barrier = threading.Barrier(2)

        def worker():
            from django.db import connection
            connection.close()  # fresh connection per thread
            try:
                barrier.wait(timeout=5)
                results.append(
                    _process_collection_sync(
                        customer=self.customer,
                        cash_amount=Decimal("100.00"),
                        transfer_amount=Decimal("0.00"),
                        collected_by_id=self.user.pk,
                    )
                )
            except (OverpaymentError, NoConfirmableInvoicesError):
                results.append(None)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(PaymentTransaction.objects.count(), 1)
        from django.db.models import Sum
        allocated = PaymentAllocation.objects.filter(invoice=invoice).aggregate(
            total=Sum("cash_amount") + Sum("transfer_amount")
        )["total"] or Decimal("0")
        self.assertEqual(allocated, Decimal("100.00"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)


class PaymentAPITests(PaymentTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user()
        self.customer = Customer.objects.create(name="Acme")
        self.product = self.create_product()
        self.invoice = self.create_invoice(
            self.customer, self.user, self.product, quantity=1
        )
        self.factory = AsyncRequestFactory()

    async def test_collection_endpoint(self):
        request = self.factory.post(
            "/api/v1/payments/collections/",
            {
                "customer": self.customer.pk,
                "cash_amount": "100.00",
                "transfer_amount": "0.00",
            },
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        response = await CollectionView.as_view()(request)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["cash_amount"], "100.00")
        self.assertEqual(len(response.data["allocations"]), 1)

    async def test_collection_rejects_overpayment(self):
        request = self.factory.post(
            "/api/v1/payments/collections/",
            {
                "customer": self.customer.pk,
                "cash_amount": "999.00",
                "transfer_amount": "0.00",
            },
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        response = await CollectionView.as_view()(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "overpayment")

    async def test_collection_rejects_negative(self):
        request = self.factory.post(
            "/api/v1/payments/collections/",
            {
                "customer": self.customer.pk,
                "cash_amount": "-5.00",
                "transfer_amount": "0.00",
            },
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        response = await CollectionView.as_view()(request)
        self.assertEqual(response.status_code, 400)

    async def test_collection_zero_is_noop(self):
        request = self.factory.post(
            "/api/v1/payments/collections/",
            {
                "customer": self.customer.pk,
                "cash_amount": "0.00",
                "transfer_amount": "0.00",
            },
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        response = await CollectionView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "noop")
        self.assertFalse(await PaymentTransaction.objects.aexists())

    async def test_transaction_list_read_only(self):
        await sync_to_async(
            lambda: _process_collection_sync(
                customer=self.customer,
                cash_amount=Decimal("50.00"),
                transfer_amount=Decimal("0.00"),
                collected_by_id=self.user.pk,
            ),
            thread_sensitive=True,
        )()
        request = self.factory.get("/api/v1/payments/transactions/")
        force_authenticate(request, user=self.user)
        response = await TransactionListView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
