import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmployeeShift",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("business_date", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[("open", "Open"), ("closed", "Closed")],
                        db_index=True,
                        default="open",
                        max_length=10,
                    ),
                ),
                ("opened_at", models.DateTimeField(auto_now_add=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "opening_cash",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=14,
                        validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                    ),
                ),
                (
                    "closing_cash",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=14,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                    ),
                ),
                (
                    "closing_transfer",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=14,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                    ),
                ),
                ("closing_notes", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="shifts",
                        to="accounts.employee",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="employee_shifts",
                        to="organization.site",
                    ),
                ),
                (
                    "vehicle",
                    models.ForeignKey(
                        blank=True,
                        limit_choices_to={"location_type": "SALES_VEHICLE"},
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="employee_shifts",
                        to="inventory.stocklocation",
                    ),
                ),
            ],
            options={
                "ordering": ("-business_date", "-opened_at"),
                "permissions": (
                    ("start_employee_shift", "Can start an employee shift"),
                    ("close_employee_shift", "Can close an employee shift"),
                    ("view_all_employee_shifts", "Can view all employee shifts"),
                ),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("employee", "business_date"),
                        name="accounts_employee_shift_employee_date_unique",
                    ),
                    models.UniqueConstraint(
                        condition=Q(status="open"),
                        fields=("employee",),
                        name="accounts_one_open_shift_per_employee",
                    ),
                    models.CheckConstraint(
                        condition=(
                            Q(status="open", closed_at__isnull=True, closing_cash__isnull=True, closing_transfer__isnull=True)
                            | Q(status="closed", closed_at__isnull=False, closing_cash__isnull=False, closing_transfer__isnull=False)
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
                    models.CheckConstraint(
                        condition=Q(closing_transfer__isnull=True) | Q(closing_transfer__gte=0),
                        name="accounts_employee_shift_closing_transfer_non_negative",
                    ),
                ],
            },
        ),
    ]
