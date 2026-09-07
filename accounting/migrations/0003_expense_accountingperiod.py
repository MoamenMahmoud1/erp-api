import decimal

import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounting", "0002_journalentry_source_unique"),
        ("organization", "0004_department"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountingPeriod",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("is_closed", models.BooleanField(db_index=True, default=False)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "closed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="closed_accounting_periods",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="accounting_periods",
                        to="organization.company",
                    ),
                ),
            ],
            options={
                "ordering": ("-start_date",),
                "indexes": [
                    models.Index(
                        fields=("company", "start_date", "end_date"),
                        name="acct_period_company_dates_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("company", "start_date", "end_date"),
                        name="accounting_period_company_dates_unique",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Expense",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=14,
                        validators=[
                            django.core.validators.MinValueValidator(
                                decimal.Decimal("0.01")
                            )
                        ],
                    ),
                ),
                ("expense_date", models.DateField()),
                ("description", models.CharField(max_length=500)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="expenses",
                        to="organization.company",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_expenses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "expense_account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="expenses",
                        to="accounting.account",
                    ),
                ),
                (
                    "payment_account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="paid_expenses",
                        to="accounting.account",
                    ),
                ),
            ],
            options={
                "ordering": ("-expense_date", "-id"),
                "indexes": [
                    models.Index(
                        fields=("company", "expense_date"),
                        name="expense_company_date_idx",
                    )
                ],
            },
        ),
    ]
