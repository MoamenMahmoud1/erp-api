from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("payments", "0007_paymentrefund_paymenttransaction_permissions")]

    operations = [
        migrations.AlterModelOptions(
            name="paymenttransaction",
            options={
                "ordering": ("-created_at",),
                "permissions": [
                    ("process_collection", "Can process a payment collection"),
                    ("refund_payment", "Can refund a payment"),
                ],
            },
        ),
    ]
