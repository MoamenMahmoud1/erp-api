from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("inventory", "0005_remove_redundant_stockbalance_index")]

    operations = [
        migrations.AlterField(
            model_name="stockmovement",
            name="movement_type",
            field=models.CharField(
                choices=[
                    ("PURCHASE", "Purchase"),
                    ("PURCHASE_RETURN", "Purchase Return"),
                    ("TRANSFER", "Transfer"),
                    ("SALE", "Sale"),
                    ("SALEABLE_RETURN", "Saleable Return"),
                    ("DAMAGED_RETURN", "Damaged Return"),
                ],
                max_length=30,
            ),
        )
    ]
