from django.db import models


class Account(models.Model):
    class AccountType(models.TextChoices):
        ASSET = "asset", "Asset"
        LIABILITY = "liability", "Liability"
        EQUITY = "equity", "Equity"
        REVENUE = "revenue", "Revenue"
        EXPENSE = "expense", "Expense"

    company = models.ForeignKey(
        "organization.Company", on_delete=models.PROTECT, related_name="accounts"
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("code",)
        constraints = [
            models.UniqueConstraint(fields=("company", "code"), name="accounting_account_company_code_unique"),
        ]
        indexes = [models.Index(fields=("company", "account_type"), name="acct_company_type_idx")]
        permissions = [
            ("manage_chart_of_accounts", "Can manage the chart of accounts"),
            ("view_financial_reports", "Can view financial reports"),
        ]

    @property
    def normal_side(self) -> str:
        return "debit" if self.account_type in {self.AccountType.ASSET, self.AccountType.EXPENSE} else "credit"

    def __str__(self):
        return f"{self.code} - {self.name}"
