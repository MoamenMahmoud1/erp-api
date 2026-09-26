from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pushdevice",
            name="platform",
            field=models.CharField(
                choices=[
                    ("android", "Android"),
                    ("ios", "iOS"),
                    ("web", "Web"),
                ],
                max_length=20,
            ),
        ),
    ]
