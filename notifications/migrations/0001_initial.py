from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                (
                    "notification_type",
                    models.CharField(
                        choices=[
                            ("approval_requested", "Approval requested"),
                            ("approval_approved", "Approval approved"),
                            ("approval_rejected", "Approval rejected"),
                        ],
                        max_length=50,
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("body", models.TextField()),
                ("target_type", models.CharField(blank=True, max_length=100)),
                ("target_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("data", models.JSONField(blank=True, default=dict)),
                ("dedupe_key", models.CharField(max_length=255, unique=True)),
                ("read_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at", "-id"),
                "indexes": [
                    models.Index(
                        fields=["user", "read_at", "created_at"],
                        name="notif_user_read_created_idx",
                    ),
                    models.Index(
                        fields=["user", "created_at"],
                        name="notif_user_created_idx",
                    ),
                ],
            },
        ),
    ]
