from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("purchases", "0005_purchase_return_permission")]

    operations = [
        migrations.AlterField(
            model_name="purchasereturnitem",
            name="unit_price",
            field=models.DecimalField(decimal_places=2, max_digits=12),
        ),
    ]
