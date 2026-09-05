from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_employee_department_employee_work_site"),
        ("purchases", "0003_alter_purchase_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="PurchaseReturn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_purchase_returns", settings.AUTH_USER_MODEL, to_field="id")),
                ("purchase", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="returns", to="purchases.purchase")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="PurchaseReturnItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField()),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("purchase_item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="return_items", to="purchases.purchaseitem")),
                ("purchase_return", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="purchases.purchasereturn")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("purchase_return", "purchase_item"), name="purchase_return_item_unique_line"),
                    models.CheckConstraint(condition=models.Q(quantity__gte=1), name="purchase_return_item_quantity_positive"),
                    models.CheckConstraint(condition=models.Q(unit_price__gte=Decimal("0")), name="purchase_return_item_price_non_negative"),
                ]
            },
        ),
    ]
