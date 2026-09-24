from django.db import models
from django.db.models import Q
from phonenumber_field.modelfields import PhoneNumberField


class Company(models.Model):
    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=250, blank=True)

    registration_number = models.CharField(max_length=100, blank=True)
    tax_number = models.CharField(max_length=100, blank=True)

    email = models.EmailField(blank=True)
    phone = PhoneNumberField(blank=True)
    website = models.URLField(blank=True)

    singleton_marker = models.BooleanField(
        default=True,
        editable=False,
    )

    # Transactional counters used for cheap master-data dashboard metrics.
    # They are maintained on writes and reconciled by a daily background job.
    product_count = models.PositiveBigIntegerField(default=0)
    invoice_count = models.PositiveBigIntegerField(default=0)
    customer_count = models.PositiveBigIntegerField(default=0)
    supplier_count = models.PositiveBigIntegerField(default=0)
    counters_reconciled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        constraints = [
            models.CheckConstraint(
                condition=Q(singleton_marker=True),
                name="organization_company_singleton_marker_true",
            ),
            models.UniqueConstraint(
                fields=("singleton_marker",),
                name="organization_only_one_company",
            ),
        ]

    def __str__(self):
        return self.name
