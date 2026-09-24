from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0002_performance_indexes"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(fields=("created_at", "id"), name="stock_move_created_id_idx"),
        ),
    ]
