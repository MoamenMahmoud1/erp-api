import decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


def backfill_stock_valuation(apps, schema_editor):
    StockBalance = apps.get_model("inventory", "StockBalance")
    for balance in StockBalance.objects.select_related("product").iterator():
        purchase_price = balance.product.purchase_price or decimal.Decimal("0.00")
        balance.total_cost = (decimal.Decimal(balance.quantity) * purchase_price).quantize(decimal.Decimal("0.01"))
        balance.save(update_fields=("total_cost",))


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0008_stockmovement_integrity_and_item_index"),
    ]

    operations = [
        migrations.AddField(model_name="stockmovementitem", name="unit_cost", field=models.DecimalField(blank=True, decimal_places=2, help_text="Historical inventory cost per unit captured at movement time.", max_digits=14, null=True, validators=[MinValueValidator(decimal.Decimal("0"))])),
        migrations.AddField(model_name="stockbalance", name="total_cost", field=models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=16, validators=[MinValueValidator(decimal.Decimal("0"))])),
        migrations.AddConstraint(model_name="stockmovementitem", constraint=models.CheckConstraint(condition=models.Q(unit_cost__gte=decimal.Decimal("0")) | models.Q(unit_cost__isnull=True), name="stock_movement_item_unit_cost_non_negative")),
        migrations.AddConstraint(model_name="stockbalance", constraint=models.CheckConstraint(condition=models.Q(total_cost__gte=decimal.Decimal("0")), name="stock_balance_total_cost_non_negative")),
        migrations.RunPython(backfill_stock_valuation, migrations.RunPython.noop),
    ]
