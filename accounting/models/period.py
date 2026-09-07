from django.conf import settings
from django.db import models


class AccountingPeriod(models.Model):
    """Date range that can be closed to prevent new accounting postings."""

    company = models.ForeignKey(
        "organization.Company",
        on_delete=models.PROTECT,
        related_name="accounting_periods",
    )
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False, db_index=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="closed_accounting_periods",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-start_date",)
        constraints = [
            models.UniqueConstraint(
                fields=("company", "start_date", "end_date"),
                name="accounting_period_company_dates_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=("company", "start_date", "end_date"),
                name="acct_period_company_dates_idx",
            ),
        ]

    def __str__(self):
        return self.name
