from decimal import Decimal
import threading

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.models import Sum
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from customers.models import Customer
from invoices.models import Invoice, InvoiceItem
from payments.api.views import CollectionView, TransactionListView
from payments.models import IdempotencyKey, PaymentAllocation, PaymentTransaction
from payments.services import (
    NoConfirmableInvoicesError,
    OverpaymentError,
    ProcessCollectionIdempotent,
    _process_collection,
)
from products.models import Product


class PaymentTestMixin:
    def create_user(self, username="cashier", staff=True):
        return get_user_model().objects.create_user(
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

    def create_invoice(self, customer, user, product, quantity=1, unit_price="100.00", status=Invoice.Status.CONFIRMED):
        invoice = Invoice.objects.create(customer=customer, created_by=user, status=status)
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

    def collect(self, cash, transfer):
        return _process_collection(
            customer=self.customer,
            cash_amount=Decimal(cash),
            transfer_amount=Decimal(transfer),
            collected_by_id=self.user.pk,
        )

    def test_full_cash_marks_invoice_paid(self):
        invoice = self.create_invoice(self.customer, self.user, self.product)
        tx = self.collect("100", "0")
        self.assertEqual(tx.cash_amount, Decimal("100.00"))
        self.assertEqual(PaymentAllocation.objects.get(transaction=tx, invoice=invoice).total_amount, Decimal("100.00"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)

    def test_partial_payment(self):
        invoice = self.create_invoice(self.customer, self.user, self.product)
        self.collect("30", "0")
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.CONFIRMED)
        self.assertEqual(invoice.outstanding_amount, Decimal("70.00"))

    def test_multi_invoice_oldest_first(self):
        old = self.create_invoice(self.customer, self.user, self.product)
        new = self.create_invoice(self.customer, self.user, self.product, unit_price="50")
        tx = self.collect("120", "0")
        self.assertEqual(PaymentAllocation.objects.get(transaction=tx, invoice=old).total_amount, Decimal("100.00"))
        self.assertEqual(PaymentAllocation.objects.get(transaction=tx, invoice=new).total_amount, Decimal("20.00"))

    def test_overpayment_rolls_back(self):
        self.create_invoice(self.customer, self.user, self.product)
        with self.assertRaises(OverpaymentError):
            self.collect("101", "0")
        self.assertFalse(PaymentTransaction.objects.exists())

    def test_no_confirmable_invoice(self):
        self.create_invoice(self.customer, self.user, self.product, status=Invoice.Status.DRAFT)
        with self.assertRaises(NoConfirmableInvoicesError):
            self.collect("10", "0")

    def test_idempotency_replays_same_result(self):
        invoice = self.create_invoice(self.customer, self.user, self.product)
        data = {
            "customer": invoice.customer_id,
            "cash_amount": "100.00",
            "transfer_amount": "0.00",
        }
        first = ProcessCollectionIdempotent()(
            key="collection-1",
            user_id=self.user.pk,
            path="/api/v1/payments/collections/",
            data=data,
            customer=self.customer,
            cash_amount=Decimal("100"),
            transfer_amount=Decimal("0"),
        )
        second = ProcessCollectionIdempotent()(
            key="collection-1",
            user_id=self.user.pk,
            path="/api/v1/payments/collections/",
            data=data,
            customer=self.customer,
            cash_amount=Decimal("100"),
            transfer_amount=Decimal("0"),
        )
        self.assertEqual(first.response_status, 201)
        self.assertEqual(second.response_body, first.response_body)
        self.assertEqual(PaymentTransaction.objects.count(), 1)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)

    def test_allocation_unique_constraint(self):
        invoice = self.create_invoice(self.customer, self.user, self.product)
        tx = self.collect("100", "0")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PaymentAllocation.objects.create(
                    transaction=tx,
                    invoice=invoice,
                    cash_amount=Decimal("1"),
                    transfer_amount=Decimal("0"),
                )

    def test_concurrent_collections_cannot_double_allocate(self):
        invoice = self.create_invoice(self.customer, self.user, self.product)
        barrier = threading.Barrier(2)
        errors = []

        def worker():
            connection.close()
            try:
                barrier.wait(timeout=5)
                _process_collection(
                    customer=self.customer,
                    cash_amount=Decimal("100"),
                    transfer_amount=Decimal("0"),
                    collected_by_id=self.user.pk,
                )
            except (OverpaymentError, NoConfirmableInvoicesError):
                errors.append(True)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertEqual(PaymentTransaction.objects.count(), 1)
        total = PaymentAllocation.objects.filter(invoice=invoice).aggregate(
            total=Sum("cash_amount") + Sum("transfer_amount")
        )["total"]
        self.assertEqual(total, Decimal("100.00"))


class PaymentAPITests(PaymentTestMixin, TestCase):
    def setUp(self):
        self.user = self.create_user()
        self.customer = Customer.objects.create(name="Acme")
        self.product = self.create_product()
        self.invoice = self.create_invoice(self.customer, self.user, self.product)
        self.factory = APIRequestFactory()

    def post_collection(self, cash="100.00", transfer="0.00", key="test-key"):
        request = self.factory.post(
            "/api/v1/payments/collections/",
            {
                "customer": self.customer.pk,
                "cash_amount": cash,
                "transfer_amount": transfer,
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        force_authenticate(request, user=self.user)
        return CollectionView.as_view()(request)

    def test_collection_endpoint(self):
        response = self.post_collection()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["cash_amount"], "100.00")

    def test_collection_requires_idempotency_key(self):
        request = self.factory.post(
            "/api/v1/payments/collections/",
            {"customer": self.customer.pk, "cash_amount": "10.00", "transfer_amount": "0.00"},
            format="json",
        )
        force_authenticate(request, user=self.user)
        response = CollectionView.as_view()(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "idempotency_key_required")

    def test_duplicate_key_does_not_duplicate_payment(self):
        first = self.post_collection(cash="50.00", key="same-key")
        second = self.post_collection(cash="50.00", key="same-key")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.data, second.data)
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_same_key_with_different_body_is_conflict(self):
        self.assertEqual(self.post_collection(cash="20.00", key="same-key").status_code, 201)
        response = self.post_collection(cash="30.00", key="same-key")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "idempotency_conflict")

    def test_transaction_list(self):
        self.post_collection(cash="50.00")
        request = self.factory.get("/api/v1/payments/transactions/")
        force_authenticate(request, user=self.user)
        response = TransactionListView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
