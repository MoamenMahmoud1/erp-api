from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from phonenumber_field.modelfields import PhoneNumberField

from .company import Company

from django.core.validators import RegexValidator


class Site(models.Model):
    class Type(models.TextChoices):
        HEAD_OFFICE = "head_office", "Head office"
        BRANCH = "branch", "Branch"
        STORE = "store", "Store"

    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="sites",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )

    code = models.CharField(max_length=40)
    name = models.CharField(max_length=200)
    site_type = models.CharField(
        max_length=20,
        choices=Type.choices,
    )

    address_line_1 = models.CharField(max_length=250)
    address_line_2 = models.CharField(max_length=250, blank=True)
    city = models.CharField(max_length=100)
    state_or_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    country_code = models.CharField(
    max_length=2,
    validators=[
        RegexValidator(
            regex=r"^[A-Za-z]{2}$",
            message="Enter a valid two-letter country code.",
        ),
    ],
)

    email = models.EmailField(blank=True)
    phone = PhoneNumberField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("code",)
        constraints = [
            models.UniqueConstraint(
                Lower("code"),
                "company",
                name="organization_site_company_code_ci_unique",
            ),
            models.UniqueConstraint(
                fields=("company",),
                condition=Q(site_type="head_office"),
                name="organization_one_head_office_per_company",
            ),
            models.CheckConstraint(
                condition=Q(site_type="store") | Q(parent__isnull=True),
                name="organization_only_store_may_have_parent",
            ),
        ]


    def _normalize_fields(self):
        self.code = (self.code or "").strip().upper()
        self.country_code = (self.country_code or "").strip().upper()

    def full_clean(self, *args, **kwargs):
        self._normalize_fields()
        return super().full_clean(*args, **kwargs)

    def clean(self):
        super().clean()



        if self.pk and self.parent_id == self.pk:
            raise ValidationError(
                {"parent": "A site cannot be its own parent."}
            )

        if self.parent:
            if self.parent.company_id != self.company_id:
                raise ValidationError(
                    {"parent": "The parent must belong to the same company."}
                )

            if self.site_type == self.Type.STORE:
                if self.parent.site_type != self.Type.BRANCH:
                    raise ValidationError(
                        {"parent": "A store may only belong to a branch."}
                    )
            else:
                raise ValidationError(
                    {"parent": "Only stores may belong to another site."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"