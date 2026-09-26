from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("suppliers", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="supplier",
            index=models.Index(
                fields=("name",),
                name="supplier_name_idx",
            ),
        ),
    ]
