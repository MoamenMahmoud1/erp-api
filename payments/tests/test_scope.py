from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from payments.models import PaymentTransaction
from payments.querysets import PaymentTransactionQuerySet
from .helpers import PaymentTestMixin


class PaymentScopeTests(PaymentTestMixin, TestCase):
    def test_actor_sees_own_collection(self):
        payment = PaymentTransaction.objects.create(
            customer=self.customer,
            collected_by=self.user,
            cash_amount=Decimal("10"),
            transfer_amount=Decimal("0"),
        )
        self.assertIn(payment, PaymentTransaction.objects.visible_to(self.user))

    def test_actor_cannot_see_other_collection(self):
        other = get_user_model().objects.create_user(
            username="other-payment",
            email="other-payment@example.com",
            password="StrongPass123!",
        )
        payment = PaymentTransaction.objects.create(
            customer=self.customer,
            collected_by=other,
            cash_amount=Decimal("10"),
            transfer_amount=Decimal("0"),
        )
        self.assertNotIn(payment, PaymentTransaction.objects.visible_to(self.user))
