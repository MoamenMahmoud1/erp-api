from decimal import Decimal
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounting.models import Account, AccountingPeriod, Expense, JournalEntry
from accounting.services import (
    AccountingPeriodError,
    JournalEntryError,
    close_period,
    create_expense,
    create_journal_entry,
    create_opening_balance,
    create_period,
    post_journal_entry,
    profit_and_loss,
)
from common.exceptions import InvalidBusinessOperation
from organization.models import Company


class AccountingCompletionTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Accounting Completion Company")
        self.user = get_user_model().objects.create_user(
            username="accounting-completion-user",
            email="accounting-completion@test.local",
            password="strong-password-123",
        )
        self.cash = Account.objects.create(
            company=self.company,
            code="1010",
            name="Cash",
            account_type=Account.AccountType.ASSET,
        )
        self.capital = Account.objects.create(
            company=self.company,
            code="3000",
            name="Owner Capital",
            account_type=Account.AccountType.EQUITY,
        )
        self.expense_account = Account.objects.create(
            company=self.company,
            code="5200",
            name="Operating Expenses",
            account_type=Account.AccountType.EXPENSE,
        )

    def test_expense_posts_to_expense_and_cash(self):
        expense = create_expense(
            amount=Decimal("250.00"),
            expense_account=self.expense_account.pk,
            payment_account=self.cash.pk,
            expense_date=date(2026, 1, 10),
            description="Office supplies",
            created_by_id=self.user.pk,
            company=self.company,
        )

        self.assertIsInstance(expense, Expense)
        entry = JournalEntry.objects.get(
            company=self.company,
            source_type="expense",
            source_id=expense.pk,
        )
        self.assertEqual(entry.status, JournalEntry.Status.POSTED)
        self.assertEqual(
            entry.lines.get(account=self.expense_account).debit,
            Decimal("250.00"),
        )
        self.assertEqual(entry.lines.get(account=self.cash).credit, Decimal("250.00"))
        self.assertEqual(
            profit_and_loss(company=self.company)["total_expenses"],
            Decimal("250.00"),
        )

    def test_opening_balance_is_single_posted_entry(self):
        entry = create_opening_balance(
            entry_date=date(2026, 1, 1),
            lines=[
                {"account_id": self.cash.pk, "debit": Decimal("1000.00"), "credit": 0},
                {"account_id": self.capital.pk, "debit": 0, "credit": Decimal("1000.00")},
            ],
            created_by_id=self.user.pk,
            company=self.company,
        )

        self.assertEqual(entry.status, JournalEntry.Status.POSTED)
        self.assertEqual(entry.source_type, "opening_balance")
        self.assertEqual(entry.source_id, self.company.pk)
        with self.assertRaises(InvalidBusinessOperation):
            create_opening_balance(
                entry_date=date(2026, 1, 1),
                lines=[
                    {"account_id": self.cash.pk, "debit": Decimal("10.00"), "credit": 0},
                    {"account_id": self.capital.pk, "debit": 0, "credit": Decimal("10.00")},
                ],
                created_by_id=self.user.pk,
                company=self.company,
            )

    def test_closed_period_blocks_new_journals_and_requires_no_drafts(self):
        period = create_period(
            name="January 2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            company=self.company,
        )
        draft = create_journal_entry(
            created_by_id=self.user.pk,
            entry_date=date(2026, 1, 15),
            description="Initial capital",
            lines=[
                {"account_id": self.cash.pk, "debit": Decimal("100.00"), "credit": 0},
                {"account_id": self.capital.pk, "debit": 0, "credit": Decimal("100.00")},
            ],
            company=self.company,
        )

        with self.assertRaises(AccountingPeriodError):
            close_period(
                period_id=period.pk,
                actor_id=self.user.pk,
                company=self.company,
            )

        post_journal_entry(
            entry_id=draft.pk,
            actor_id=self.user.pk,
            company=self.company,
        )
        period = close_period(
            period_id=period.pk,
            actor_id=self.user.pk,
            company=self.company,
        )
        self.assertTrue(period.is_closed)
        self.assertEqual(AccountingPeriod.objects.get(pk=period.pk).closed_by_id, self.user.pk)

        with self.assertRaises(AccountingPeriodError):
            create_journal_entry(
                created_by_id=self.user.pk,
                entry_date=date(2026, 1, 20),
                description="Blocked entry",
                lines=[
                    {"account_id": self.cash.pk, "debit": Decimal("20.00"), "credit": 0},
                    {"account_id": self.capital.pk, "debit": 0, "credit": Decimal("20.00")},
                ],
                company=self.company,
            )
