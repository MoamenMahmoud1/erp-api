from django.db import migrations


def backfill_legacy_batches(apps, schema_editor):
    StockBalance = apps.get_model("inventory", "StockBalance")
    InventoryBatch = apps.get_model("inventory", "InventoryBatch")
    StockBatchBalance = apps.get_model("inventory", "StockBatchBalance")

    db_alias = schema_editor.connection.alias
    for balance in StockBalance.objects.using(db_alias).filter(quantity__gt=0).iterator():
        if StockBatchBalance.objects.using(db_alias).filter(
            location_id=balance.location_id,
            batch__product_id=balance.product_id,
            quantity__gt=0,
        ).exists():
            continue

        batch = InventoryBatch.objects.using(db_alias).create(
            product_id=balance.product_id,
            batch_number=None,
            manufactured_date=None,
            expiry_date=None,
        )
        StockBatchBalance.objects.using(db_alias).create(
            location_id=balance.location_id,
            batch_id=batch.pk,
            quantity=balance.quantity,
            total_cost=balance.total_cost,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0013_batch_tracking"),
    ]

    operations = [
        migrations.RunPython(backfill_legacy_batches, migrations.RunPython.noop),
    ]
