from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0014_backfill_legacy_batches"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="stockbatchbalance",
            new_name="sbb_loc_qty_idx",
            old_name="stock_batch_balance_location_qty_idx",
        ),
        migrations.RenameIndex(
            model_name="stockbatchbalance",
            new_name="sbb_batch_loc_idx",
            old_name="stock_batch_balance_batch_loc_idx",
        ),
    ]
