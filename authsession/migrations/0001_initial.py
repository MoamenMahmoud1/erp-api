import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def move_content_type(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.using(schema_editor.connection.alias).filter(
        app_label="accounts",
        model="authsession",
    ).update(app_label="authsession")


def restore_content_type(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.using(schema_editor.connection.alias).filter(
        app_label="authsession",
        model="authsession",
    ).update(app_label="accounts")


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0005_move_authsession_state"),
    ]
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(move_content_type, restore_content_type),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="AuthSession",
                    fields=[
                        (
                            "id",
                            models.UUIDField(
                                default=uuid.uuid4,
                                editable=False,
                                primary_key=True,
                                serialize=False,
                            ),
                        ),
                        (
                            "device_id",
                            models.UUIDField(
                                db_index=True,
                                default=uuid.uuid4,
                                editable=False,
                            ),
                        ),
                        ("device_name", models.CharField(blank=True, max_length=100)),
                        ("user_agent", models.TextField(blank=True)),
                        (
                            "ip_address",
                            models.GenericIPAddressField(blank=True, null=True),
                        ),
                        ("current_refresh_jti", models.UUIDField(unique=True)),
                        ("expires_at", models.DateTimeField(db_index=True)),
                        ("revoked_at", models.DateTimeField(blank=True, null=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        (
                            "last_refreshed_at",
                            models.DateTimeField(default=django.utils.timezone.now),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="auth_sessions",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "db_table": "accounts_authsession",
                        "ordering": ("-created_at",),
                        "indexes": [
                            models.Index(
                                fields=["user", "revoked_at"],
                                name="accounts_auth_user_rev_idx",
                            ),
                        ],
                    },
                ),
            ],
        ),
    ]
