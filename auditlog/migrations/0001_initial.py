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
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=100)),
                ("entity_type", models.CharField(max_length=100)),
                ("entity_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("request_id", models.CharField(blank=True, max_length=128)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="audit_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at", "-id"),
            },
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=("entity_type", "entity_id", "created_at"), name="audit_entity_created_idx"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=("actor", "created_at"), name="audit_actor_created_idx"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=("action", "created_at"), name="audit_action_created_idx"),
        ),
    ]
