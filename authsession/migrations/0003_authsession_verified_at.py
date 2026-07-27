from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("authsession", "0002_authsession_authsession_one_active_device"),
    ]

    operations = [
        migrations.AddField(
            model_name="authsession",
            name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
