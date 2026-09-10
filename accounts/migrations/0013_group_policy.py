from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_role_scope_least_privilege"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Role",
            new_name="GroupPolicy",
        ),
        migrations.AlterField(
            model_name="grouppolicy",
            name="group",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="policy",
                to="auth.group",
            ),
        ),
        migrations.RemoveField(
            model_name="grouppolicy",
            name="code",
        ),
        migrations.RemoveField(
            model_name="grouppolicy",
            name="is_system",
        ),
        migrations.AlterModelOptions(
            name="grouppolicy",
            options={
                "ordering": ("-level", "group__name", "pk"),
                "verbose_name": "Group policy",
                "verbose_name_plural": "Group policies",
            },
        ),
    ]
