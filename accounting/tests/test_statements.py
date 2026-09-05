from decimal import Decimal

from django.test import TestCase

from accounting.models import Account
from accounting.services import balance_sheet, cash_flow, create_journal_entry, post_journal_entry, profit_and_loss
from accounts.models import CustomUserModel
from organization.models import Company


class FinancialStatementTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Statements Company")
        self.user = CustomUserModel.objects.create_user(
            email="statements@test.local",
            password="strong-password-123",
        )
        self.cash = Account.objects.create(
            company=self.company, code="1010", name="Cash", account_type=Account.AccountType.ASSET
        )
        self.bank = Account.objects.create(
            company=self.company, code="1020", name="Bank", account_type=Account.AccountType.ASSET
        )
        self.inventory = Account.objects.create(
            company=self.company, code="1100", name="Inventory", account_type=Account.AccountType.ASSET
        )
        self.ap = Account.objects.create(
            company=self.company, code="2100", name="Accounts Payable", account_type=Account.AccountType.LIABILITY
        )
        self.sales = Account.objects.create(
            company=self.company, code="4100", name="Sales", account_type=Account.AccountType.REVENUE
        )
        self.cogs = Account.objects.create(
            company=self.company, code="5100", name="COGS", account_type=Account.AccountType.EXPENSE
        )

    def _post(self, date, lines, source_type="manual.statement", source_id=None):
        entry = create_journal_entry(
            created_by_id=self.user.pk,
            entry_date=date,
            source_type=source_type,
            source_id=source_id,
            lines=lines,
            company=self.company,
        )
        return post_journal_entry(entry_id=entry.pk, actor_id=self.user.pk, company=self.company)

    def test_profit_and_loss(self):
        self._post(
            "2026-09-01",
            [
                {"account_id": self.cash.pk, "debit": Decimal("1000"), "credit": 0},
                {"account_id": self.sales.pk, "debit": 0, "credit": Decimal("1000")},
            ],
            source_type="payment.collection",
            source_id=1,
        )
        self._post(
            "2026-09-02",
            [
                {"account_id": self.cogs.pk, "debit": Decimal("400"), "credit": 0},
                {"account_id": self.inventory.pk, "debit": 0, "credit": Decimal("400")},
            ],
            source_type="purchase.confirmation",
            source_id=1,
        )
        result = profit_and_loss(date_from="2026-09-01", date_to="2026-09-30", company=self.company)
        self.assertEqual(result["total_revenue"], Decimal("1000"))
        self.assertEqual(result["total_expenses"], Decimal("400"))
        self.assertEqual(result["net_income"], Decimal("600"))

    def test_balance_sheet_includes_current_net_income_in_equity(self):
        self._post(
            "2026-09-01",
            [
                {"account_id": self.cash.pk, "debit": Decimal("1600"), "credit": 0},
                {"account_id": self.sales.pk, "debit": 0, "credit": Decimal("1600")},
            ],
            source_type="payment.collection",
            source_id=2,
        )
        self._post(
            "2026-09-02",
            [
                {"account_id": self.cogs.pk, "debit": Decimal("600"), "credit": 0},
                {"account_id": self.inventory.pk, "debit": 0, "credit": Decimal("600")},
            ],
            source_type="purchase.confirmation",
            source_id=2,
        )
        result = balance_sheet(as_of="2026-09-30", company=self.company)
        self.assertEqual(result["total_assets"], Decimal("1000"))
        self.assertEqual(result["total_liabilities"], Decimal("0"))
        self.assertEqual(result["total_equity"], Decimal("1000"))
        self.assertTrue(result["balanced"])

    def test_cash_flow_reconciles_opening_and_ending_cash(self):
        self._post(
            "2026-09-01",
            [
                {"account_id": self.cash.pk, "debit": Decimal("500"), "credit": 0},
                {"account_id": self.sales.pk, "debit": 0, "credit": Decimal("500")},
            ],
            source_type="payment.collection",
            source_id=3,
        )
        self._post(
            "2026-08-31",
            [
                {"account_id": self.cash.pk, "debit": Decimal("250"), "credit": 0},
                {"account_id": self.ap.pk, "debit": 0, "credit": Decimal("250")},
            ],
            source_type="payment.supplier",
            source_id=4,
        )
        result = cash_flow(date_from="2026-09-01", date_to="2026-09-30", company=self.company)
        self.assertEqual(result["opening_cash"], Decimal("250"))
        self.assertEqual(result["net_change"], Decimal("500"))
        self.assertEqual(result["ending_cash"], Decimal("750"))
        self.assertEqual(result["operating"], Decimal("500"))
