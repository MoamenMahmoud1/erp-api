from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="paymenttransaction",
            index=models.Index(fields=("collected_by", "created_at"), name="pay_tx_collector_created_idx"),
        ),
        migrations.AddIndex(
            model_name="paymenttransaction",
            index=models.Index(fields=("created_at", "id"), name="pay_tx_created_id_idx"),
        ),
    ]
