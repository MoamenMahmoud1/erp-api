from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from payments.api.views import CollectionView, RefundView, TransactionListView
from payments.models import PaymentTransaction
from payments.services import collect

from .helpers import PaymentTestMixin


class PaymentAPITests(PaymentTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.invoice = self.create_invoice()
        self.factory = APIRequestFactory()

    def post_collection(self, cash="100.00", key="collection-key"):
        request = self.factory.post(
            "/api/v1/payments/collections/",
            {
                "customer": self.customer.pk,
                "cash_amount": cash,
                "transfer_amount": "0.00",
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

    def test_refund_endpoint(self):
        tx = collect(
            customer=self.customer,
            cash_amount=Decimal("100"),
            transfer_amount=Decimal("0"),
            collected_by_id=self.user.pk,
            actor=self.user,
        )
        request = self.factory.post(
            "/api/v1/payments/refunds/",
            {
                "transaction": tx.pk,
                "invoice": self.invoice.pk,
                "amount": "40.00",
            },
            format="json",
        )
        force_authenticate(request, user=self.user)
        response = RefundView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_transaction_list(self):
        collect(
            customer=self.customer,
            cash_amount=Decimal("20"),
            transfer_amount=Decimal("0"),
            collected_by_id=self.user.pk,
            actor=self.user,
        )
        request = self.factory.get("/api/v1/payments/transactions/")
        force_authenticate(request, user=self.user)
        response = TransactionListView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(PaymentTransaction.objects.count(), 1)
