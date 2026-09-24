from django.db import models


class Account(models.Model):
    class AccountType(models.TextChoices):
        ASSET = "asset", "Asset"
        LIABILITY = "liability", "Liability"
        EQUITY = "equity", "Equity"
        REVENUE = "revenue", "Revenue"
        EXPENSE = "expense", "Expense"

    company = models.ForeignKey("organization.Company", on_delete=models.PROTECT, related_name="accounts")
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
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

    def clean(self):
        super().clean()
        if self.parent_id is None:
            return
        if self.pk is not None and self.parent_id == self.pk:
            from django.core.exceptions import ValidationError
            raise ValidationError({"parent": "An account cannot be its own parent."})

        parent = self.parent
        if parent.company_id != self.company_id:
            from django.core.exceptions import ValidationError
            raise ValidationError({"parent": "The parent account must belong to the same company."})

        from django.core.exceptions import ValidationError
        visited = {self.pk} if self.pk is not None else set()
        current = parent
        while current is not None:
            if current.pk in visited:
                raise ValidationError({"parent": "The account hierarchy cannot contain cycles."})
            visited.add(current.pk)
            current = current.parent

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def normal_side(self) -> str:
        return "debit" if self.account_type in {self.AccountType.ASSET, self.AccountType.EXPENSE} else "credit"

    def __str__(self):
        return f"{self.code} - {self.name}"
