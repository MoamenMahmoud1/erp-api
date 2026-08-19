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