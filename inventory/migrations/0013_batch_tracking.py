from django.db import migrations, models
import django.db.models.deletion
from django.db.models import F, Q
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0012_stockmovement_shift"),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("batch_number", models.CharField(blank=True, max_length=100, null=True)),
                ("manufactured_date", models.DateField(blank=True, null=True)),
                ("expiry_date", models.DateField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="inventory_batches", to="products.product")),
            ],
            options={
                "ordering": ("expiry_date", "id"),
                "indexes": [models.Index(fields=("product", "expiry_date"), name="inventory_batch_expiry_idx")],
            },
        ),
        migrations.AddConstraint(
            model_name="inventorybatch",
            constraint=models.UniqueConstraint(
                condition=Q(batch_number__isnull=False),
                fields=("product", "batch_number"),
                name="inventory_batch_product_number_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="inventorybatch",
            constraint=models.CheckConstraint(
                condition=Q(expiry_date__isnull=True) | Q(manufactured_date__isnull=True) | Q(expiry_date__gte=F("manufactured_date")),
                name="inventory_batch_dates_ordered",
            ),
        ),
        migrations.CreateModel(
            name="StockBatchBalance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=0)),
                ("total_cost", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=16)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stock_balances", to="inventory.inventorybatch")),
                ("location", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stock_batch_balances", to="inventory.stocklocation")),
            ],
            options={
                "ordering": ("batch__expiry_date", "batch_id"),
                "indexes": [
                    models.Index(fields=("location", "quantity"), name="stock_batch_balance_location_qty_idx"),
                    models.Index(fields=("batch", "location"), name="stock_batch_balance_batch_loc_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="stockbatchbalance",
            constraint=models.UniqueConstraint(fields=("location", "batch"), name="stock_batch_balance_unique_location_batch"),
        ),
        migrations.AddConstraint(
            model_name="stockbatchbalance",
            constraint=models.CheckConstraint(condition=Q(quantity__gte=0), name="stock_batch_balance_quantity_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="stockbatchbalance",
            constraint=models.CheckConstraint(condition=Q(total_cost__gte=Decimal("0.00")), name="stock_batch_balance_total_cost_non_negative"),
        ),
        migrations.AddField(
            model_name="stockmovementitem",
            name="batch",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="movement_items", to="inventory.inventorybatch"),
        ),
    ]
