from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0004_alter_invoice_options"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="InvoiceReturn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_invoice_returns", to=settings.AUTH_USER_MODEL)),
                ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="returns", to="invoices.invoice")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="InvoiceReturnItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(validators=[MinValueValidator(1)])),
                ("condition", models.CharField(choices=[("saleable", "Saleable")], default="saleable", max_length=20)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=12, validators=[MinValueValidator(Decimal("0"))])),
                ("invoice_item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="return_items", to="invoices.invoiceitem")),
                ("invoice_return", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="invoices.invoicereturn")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("invoice_return", "invoice_item"), name="invoice_return_item_unique_line"),
                    models.CheckConstraint(condition=models.Q(quantity__gte=1), name="invoice_return_item_quantity_positive"),
                    models.CheckConstraint(condition=models.Q(unit_price__gte=Decimal("0")), name="invoice_return_item_price_non_negative"),
                ],
            },
        ),
    ]
