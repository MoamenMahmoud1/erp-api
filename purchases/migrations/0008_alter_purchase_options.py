from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("purchases", "0007_supplierpayment_supplierpaymentallocation")]

    operations = [
        migrations.AlterModelOptions(
            name="purchase",
            options={
                "ordering": ("-created_at",),
                "permissions": [
                    ("confirm_purchase", "Can confirm purchase"),
                    ("cancel_purchase", "Can cancel purchase"),
                    ("return_purchase", "Can return items from a purchase"),
                    ("process_supplier_payment", "Can process a supplier payment"),
                ],
            },
        ),
    ]
