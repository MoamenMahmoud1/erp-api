from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="employeeshift",
            index=models.Index(fields=("site", "business_date", "opened_at"), name="shift_site_date_opened_idx"),
        ),
    ]
