from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("purchases", "0008_alter_purchase_options"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="supplierpayment",
            old_name="supplier_payment_supplier_created_idx",
            new_name="suppay_supplier_created_idx",
        ),
    ]
