from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="stocklocation",
            index=models.Index(
                fields=("site", "is_active"),
                name="stock_loc_site_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stocklocation",
            index=models.Index(
                fields=("location_type", "is_active"),
                name="stock_loc_type_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockbalance",
            index=models.Index(
                fields=("product",),
                name="stock_balance_product_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(
                fields=("created_by", "created_at"),
                name="stock_move_creator_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(
                fields=("shift", "created_at"),
                name="stock_move_shift_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(
                fields=("source_location", "created_at"),
                name="stock_move_source_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(
                fields=("destination_location", "created_at"),
                name="stock_move_dest_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stocktransferrequestitem",
            index=models.Index(
                fields=("product",),
                name="stock_req_item_product_idx",
            ),
        ),
    ]
