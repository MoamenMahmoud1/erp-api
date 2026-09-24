from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0003_remove_redundant_idempotency_key_index"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="paymenttransaction",
            options={
                "ordering": ("-created_at",),
                "permissions": [
                    ("process_collection", "Can process a payment collection"),
                    ("refund_payment", "Can refund a payment"),
                    ("approve_bank_transfer", "Can approve a bank transfer"),
                ],
            },
        ),
    ]
