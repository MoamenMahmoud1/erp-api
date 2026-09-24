from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Expense(models.Model):
    """A paid operating expense posted directly to an expense account."""

    company = models.ForeignKey(
        "organization.Company",
        on_delete=models.PROTECT,
        related_name="expenses",
    )
    expense_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        related_name="expenses",
    )
    payment_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        related_name="paid_expenses",
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    expense_date = models.DateField()
    description = models.CharField(max_length=500)
    reference = models.CharField(max_length=120, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_expenses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-expense_date", "-id")
        indexes = [
            models.Index(fields=("company", "expense_date"), name="expense_company_date_idx"),
        ]

    def __str__(self):
        return f"Expense #{self.pk}"
