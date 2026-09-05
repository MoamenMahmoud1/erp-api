from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("inventory", "0006_purchase_return_movement")]

    operations = [
        migrations.AlterModelOptions(
            name="stockmovement",
            options={
                "ordering": ("-created_at",),
                "permissions": [("transfer_stock", "Can transfer stock")],
            },
        ),
    ]
