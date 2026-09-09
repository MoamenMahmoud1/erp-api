from django.db import migrations, models


def restrict_existing_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.update(scope="site")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_role_scope_employee_shift"),
    ]

    operations = [
        migrations.AlterField(
            model_name="role",
            name="scope",
            field=models.CharField(
                choices=[("company", "Company"), ("branch", "Branch"), ("site", "Site")],
                db_index=True,
                default="site",
                max_length=20,
            ),
        ),
        migrations.RunPython(restrict_existing_roles, migrations.RunPython.noop),
    ]
