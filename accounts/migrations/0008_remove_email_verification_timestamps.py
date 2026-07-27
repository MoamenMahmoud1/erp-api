from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_emailverificationrequest"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="emailverificationrequest",
            name="created_at",
        ),
        migrations.RemoveField(
            model_name="emailverificationrequest",
            name="updated_at",
        ),
    ]
