from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from .company import Company
from .site import Site


class Department(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="departments",
    )
    site = models.ForeignKey(
        Site,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="departments",
    )

    code = models.CharField(max_length=40)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("code"),
                "company",
                name="organization_department_company_code_ci_unique",
            ),
        ]

    def _normalize_fields(self):
        self.code = (self.code or "").strip().upper()

    def full_clean(self, *args, **kwargs):
        self._normalize_fields()
        return super().full_clean(*args, **kwargs)

    def clean(self):
        super().clean()

        if not self.site:
            return

        if self.site.company_id != self.company_id:
            raise ValidationError(
                {"site": "The site must belong to the same company."}
            )

        if self.site.site_type == Site.Type.STORE:
            raise ValidationError(
                {"site": "A department cannot belong to a store."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"