from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0002_push_devices_and_deliveries"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="notificationdelivery",
            old_name="notif_delivery_status_attempt_idx",
            new_name="notif_delivery_status_attempt",
        ),
    ]
