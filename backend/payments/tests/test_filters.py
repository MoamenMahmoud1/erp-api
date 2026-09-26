from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounting.models import JournalEntry
from payments.api.filters import PaymentTransactionFilter
from payments.models import PaymentTransaction

from .helpers import PaymentTestMixin


class PaymentTransactionFilterTests(PaymentTestMixin, TestCase):
    def test_filters_by_collector_and_date(self):
        tx = PaymentTransaction.objects.create(
            customer=self.customer,
            site=self.site,
            collected_by=self.user,
            cash_amount=Decimal("25.00"),
            transfer_amount=Decimal("0.00"),
        )
        PaymentTransaction.objects.filter(pk=tx.pk).update(created_at=timezone.now() - timedelta(days=5))
        filtered = PaymentTransactionFilter(
            {
                "created_date_from": (timezone.localdate() - timedelta(days=6)).isoformat(),
                "created_date_to": (timezone.localdate() - timedelta(days=4)).isoformat(),
                "collected_by_name": "cashier",
            },
            queryset=PaymentTransaction.objects.all(),
        ).qs
        self.assertEqual(list(filtered.values_list("pk", flat=True)), [tx.pk])

    def test_transfer_status_distinguishes_pending_and_accepted(self):
        pending = PaymentTransaction.objects.create(
            customer=self.customer,
            site=self.site,
            collected_by=self.user,
            cash_amount=Decimal("0.00"),
            transfer_amount=Decimal("30.00"),
        )
        accepted = PaymentTransaction.objects.create(
            customer=self.customer,
            site=self.site,
            collected_by=self.user,
            cash_amount=Decimal("0.00"),
            transfer_amount=Decimal("40.00"),
        )
        JournalEntry.objects.create(
            company=self.company,
            number=99,
            entry_date=timezone.localdate(),
            description="Transfer approval",
            reference="Payment Transfer Approval #2",
            source_type="payment.transfer.approval",
            source_id=accepted.pk,
            status=JournalEntry.Status.POSTED,
            created_by=self.user,
            posted_by=self.user,
        )

        pending_qs = PaymentTransactionFilter(
            {"transfer_status": "pending"},
            queryset=PaymentTransaction.objects.all(),
        ).qs
        accepted_qs = PaymentTransactionFilter(
            {"transfer_status": "accepted"},
            queryset=PaymentTransaction.objects.all(),
        ).qs
        not_applicable = PaymentTransactionFilter(
            {"transfer_status": "not_applicable"},
            queryset=PaymentTransaction.objects.all(),
        ).qs

        self.assertEqual(list(pending_qs.values_list("pk", flat=True)), [pending.pk])
        self.assertEqual(list(accepted_qs.values_list("pk", flat=True)), [accepted.pk])
        self.assertFalse(not_applicable.exists())
