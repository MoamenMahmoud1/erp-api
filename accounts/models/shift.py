from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class EmployeeShift(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    employee = models.ForeignKey(
        "accounts.Employee",
        on_delete=models.PROTECT,
        related_name="shifts",
    )
    site = models.ForeignKey(
        "organization.Site",
        on_delete=models.PROTECT,
        related_name="employee_shifts",
    )
    vehicle = models.ForeignKey(
        "inventory.StockLocation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="employee_shifts",
        limit_choices_to={"location_type": "SALES_VEHICLE"},
    )
    business_date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    opening_cash = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    closing_cash = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    closing_notes = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-business_date", "-opened_at")
        constraints = [
            models.UniqueConstraint(
                fields=("employee", "business_date"),
                name="accounts_employee_shift_employee_date_unique",
            ),
            models.UniqueConstraint(
                fields=("employee",),
                condition=Q(status="open"),
                name="accounts_one_open_shift_per_employee",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="open", closed_at__isnull=True, closing_cash__isnull=True)
                    | Q(status="closed", closed_at__isnull=False, closing_cash__isnull=False)
                ),
                name="accounts_employee_shift_status_fields_consistent",
            ),
            models.CheckConstraint(
                condition=Q(opening_cash__gte=0),
                name="accounts_employee_shift_opening_cash_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(closing_cash__isnull=True) | Q(closing_cash__gte=0),
                name="accounts_employee_shift_closing_cash_non_negative",
            ),
        ]

    def clean(self):
        super().clean()
        if self.employee_id and self.site_id:
            if self.employee.work_site_id != self.site_id:
                raise ValidationError({"site": "The shift site must match the employee work site."})

        if self.vehicle_id:
            vehicle = self.vehicle
            if vehicle.location_type != "SALES_VEHICLE":
                raise ValidationError({"vehicle": "A shift vehicle must be a sales vehicle."})
            if not vehicle.is_active:
                raise ValidationError({"vehicle": "The selected vehicle is inactive."})
            if vehicle.site_id != self.site_id:
                raise ValidationError({"vehicle": "The vehicle must belong to the shift site."})
            if vehicle.employee_id != self.employee.user_id:
                raise ValidationError({"vehicle": "The vehicle must be assigned to the shift employee."})

        if self.status == self.Status.OPEN and self.closed_at is not None:
            raise ValidationError({"closed_at": "An open shift cannot have a close time."})
        if self.status == self.Status.CLOSED and self.closed_at is None:
            raise ValidationError({"closed_at": "A closed shift must have a close time."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} · {self.business_date}"