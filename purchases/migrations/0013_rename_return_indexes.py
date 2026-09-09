from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("purchases", "0012_purchaseitem_batch_and_expiry"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="purchasereturn",
            new_name="pret_site_created_idx",
            old_name="purchase_return_site_created_idx",
        ),
        migrations.RenameIndex(
            model_name="purchasereturn",
            new_name="pret_shift_created_idx",
            old_name="purchase_return_shift_created_idx",
        ),
    ]
