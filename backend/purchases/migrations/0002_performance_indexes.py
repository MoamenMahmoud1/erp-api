from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("purchases", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="purchase",
            index=models.Index(
                fields=("supplier", "created_at"),
                name="purchase_supplier_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="purchaseitem",
            index=models.Index(
                fields=("product",),
                name="purchase_item_product_idx",
            ),
        ),
    ]
