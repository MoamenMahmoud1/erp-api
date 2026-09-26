from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("purchases", "0002_performance_indexes"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="purchase",
            index=models.Index(fields=("created_at", "id"), name="purchase_created_id_idx"),
        ),
        migrations.AddIndex(
            model_name="purchase",
            index=models.Index(fields=("status", "created_at"), name="purchase_status_created_idx"),
        ),
    ]
