from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_employee_department_employee_work_site"),
        ("invoices", "0004_alter_invoice_options"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="invoice",
            constraint=models.CheckConstraint(
                condition=models.Q(coupon_discount__gte=Decimal("0")),
                name="invoice_coupon_discount_non_negative",
            ),
        ),
        migrations.CreateModel(
            name="InvoiceReturn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_invoice_returns",
                        settings.AUTH_USER_MODEL,
                        to_field="id",
                    ),
                ),
                (
                    "invoice",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="returns",
                        to="invoices.invoice",
                    ),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="InvoiceReturnItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField()),
                ("condition", models.CharField(choices=[("saleable", "Saleable")], default="saleable", max_length=20)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=12)),
                (
                    "invoice_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="return_items",
                        to="invoices.invoiceitem",
                    ),
                ),
                (
                    "invoice_return",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="invoices.invoicereturn",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("invoice_return", "invoice_item"), name="invoice_return_item_unique_line"),
                    models.CheckConstraint(condition=models.Q(quantity__gte=1), name="invoice_return_item_quantity_positive"),
                    models.CheckConstraint(condition=models.Q(unit_price__gte=Decimal("0")), name="invoice_return_item_price_non_negative"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="invoice",
            constraint=models.UniqueConstraint(
                fields=("id",),
                name="_invoice_return_migration_noop_unique",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="invoice",
            name="_invoice_return_migration_noop_unique",
        ),
    ]
