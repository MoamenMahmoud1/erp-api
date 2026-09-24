from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0002_hot_path_indexes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="idempotencykey",
            name="key",
            field=models.CharField(max_length=128),
        ),
    ]
