from decimal import Decimal

from django.db import migrations
from django.db.models import Sum


def backfill_legacy_batches(apps, schema_editor):
    StockBalance = apps.get_model("inventory", "StockBalance")
    InventoryBatch = apps.get_model("inventory", "InventoryBatch")
    StockBatchBalance = apps.get_model("inventory", "StockBatchBalance")

    db_alias = schema_editor.connection.alias
    for balance in StockBalance.objects.using(db_alias).filter(quantity__gt=0).iterator():
        tracked = StockBatchBalance.objects.using(db_alias).filter(
            location_id=balance.location_id,
            batch__product_id=balance.product_id,
        ).aggregate(quantity=Sum("quantity"), total_cost=Sum("total_cost"))
        tracked_quantity = tracked["quantity"] or 0
        tracked_cost = tracked["total_cost"] or Decimal("0.00")
        missing_quantity = balance.quantity - tracked_quantity
        if missing_quantity <= 0:
            continue

        missing_cost = max(Decimal("0.00"), balance.total_cost - tracked_cost)
        batch = InventoryBatch.objects.using(db_alias).create(
            product_id=balance.product_id,
            batch_number=None,
            manufactured_date=None,
            expiry_date=None,
        )
        StockBatchBalance.objects.using(db_alias).create(
            location_id=balance.location_id,
            batch_id=batch.pk,
            quantity=missing_quantity,
            total_cost=missing_cost,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0013_batch_tracking"),
    ]

    operations = [
        migrations.RunPython(backfill_legacy_batches, migrations.RunPython.noop),
    ]
