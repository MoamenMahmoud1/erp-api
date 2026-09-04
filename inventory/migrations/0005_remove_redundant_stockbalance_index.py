from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0004_stocklocation_inventory_one_active_main_warehouse"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="stockbalance",
            name="stock_bal_loc_prod_idx",
        ),
    ]
