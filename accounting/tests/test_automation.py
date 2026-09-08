from decimal import Decimal

from django.test import TestCase

from accounting.models import Account, JournalEntry
from accounting.services import ensure_default_accounts, post_customer_collection
from accounts.models import CustomUserModel
from customers.models import Customer
from payments.models import PaymentTransaction


class AccountingAutomationTests(TestCase):
    # Existing test methods remain unchanged above this section.
    # The fixture now expects the explicit inventory-cost-variance account
    # introduced by the valuation hardening.

    def test_default_accounts_are_created_once(self):
        first = ensure_default_accounts(self.company)
        second = ensure_default_accounts(self.company)
        self.assertEqual(first["inventory"].pk, second["inventory"].pk)
        self.assertEqual(Account.objects.filter(company=self.company).count(), 9)
