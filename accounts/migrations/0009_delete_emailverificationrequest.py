from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_remove_email_verification_timestamps"),
    ]

    operations = [
        migrations.DeleteModel(
            name="EmailVerificationRequest",
        ),
    ]
