from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounting.models import Account, JournalEntry
from accounting.services import create_journal_entry, post_journal_entry, trial_balance
from accounts.models import CustomUserModel
from organization.models import Company


class AccountingCoreTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.user = CustomUserModel.objects.create_user(
            username="accounting-user",
            email="accounting@test.local",
            password="strong-password-123",
        )
        self.cash = Account.objects.create(
            company=self.company,
            code="1000",
            name="Cash",
            account_type=Account.AccountType.ASSET,
        )
        self.sales = Account.objects.create(
            company=self.company,
            code="4000",
            name="Sales Revenue",
            account_type=Account.AccountType.REVENUE,
        )

    def test_balanced_entry_can_be_posted(self):
        entry = create_journal_entry(
            created_by_id=self.user.pk,
            entry_date=timezone.now().date(),
            description="Cash sale",
            lines=[
                {
                    "account_id": self.cash.pk,
                    "debit": Decimal("100.00"),
                    "credit": Decimal("0"),
                },
                {
                    "account_id": self.sales.pk,
                    "debit": Decimal("0"),
                    "credit": Decimal("100.00"),
                },
            ],
            company=self.company,
        )
        self.assertEqual(entry.status, JournalEntry.Status.DRAFT)
        post_journal_entry(
            entry_id=entry.pk,
            actor_id=self.user.pk,
            company=self.company,
        )
        entry.refresh_from_db()
        self.assertEqual(entry.status, JournalEntry.Status.POSTED)

        rows, total_debit, total_credit = trial_balance(company=self.company)
        self.assertEqual(total_debit, Decimal("100.00"))
        self.assertEqual(total_credit, Decimal("100.00"))
        self.assertEqual(len(rows), 2)

    def test_unbalanced_entry_is_rejected(self):
        with self.assertRaises(Exception):
            create_journal_entry(
                created_by_id=self.user.pk,
                entry_date=timezone.now().date(),
                lines=[
                    {
                        "account_id": self.cash.pk,
                        "debit": Decimal("100.00"),
                        "credit": Decimal("0"),
                    },
                    {
                        "account_id": self.sales.pk,
                        "debit": Decimal("0"),
                        "credit": Decimal("90.00"),
                    },
                ],
                company=self.company,
            )

    def test_posted_entry_cannot_be_posted_twice(self):
        entry = create_journal_entry(
            created_by_id=self.user.pk,
            entry_date=timezone.now().date(),
            lines=[
                {
                    "account_id": self.cash.pk,
                    "debit": Decimal("50.00"),
                    "credit": Decimal("0"),
                },
                {
                    "account_id": self.sales.pk,
                    "debit": Decimal("0"),
                    "credit": Decimal("50.00"),
                },
            ],
            company=self.company,
        )
        post_journal_entry(
            entry_id=entry.pk,
            actor_id=self.user.pk,
            company=self.company,
        )
        with self.assertRaises(Exception):
            post_journal_entry(
                entry_id=entry.pk,
                actor_id=self.user.pk,
                company=self.company,
            )
