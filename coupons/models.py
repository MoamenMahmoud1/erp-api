from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Coupon(models.Model):
    """A discount coupon applied to an invoice.

    Represents the coupon/discount domain. Does NOT mix in the carton/pack
    pricing concept — that now lives in ``products.CartonPricing``.
    """

    class DiscountType(models.TextChoices):
        FIXED = "fixed", "Fixed amount"
        PERCENTAGE = "percentage", "Percentage"

    code = models.SlugField(max_length=60, unique=True)
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.FIXED,
    )
    discount_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    minimum_invoice_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("code",)
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(discount_value__lt=Decimal("0")),
                name="coupon_discount_value_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    discount_type="percentage",
                    discount_value__lte=Decimal("100"),
                )
                | ~models.Q(discount_type="percentage"),
                name="coupon_discount_percentage_max_100",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    minimum_invoice_amount__isnull=True
                )
                | ~models.Q(minimum_invoice_amount__lt=Decimal("0")),
                name="coupon_minimum_invoice_amount_non_negative",
            ),
        ]

    def clean(self):
        super().clean()
        if (
            self.discount_type == self.DiscountType.PERCENTAGE
            and self.discount_value is not None
            and self.discount_value > Decimal("100")
        ):
            raise ValidationError(
                {"discount_value": "A percentage discount cannot exceed 100."}
            )
        if (
            self.valid_from
            and self.valid_until
            and self.valid_until <= self.valid_from
        ):
            raise ValidationError(
                {"valid_until": "valid_until must be after valid_from."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.code