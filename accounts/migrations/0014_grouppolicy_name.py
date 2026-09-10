from django.db import migrations, models


def copy_group_names_to_role_names(apps, schema_editor):
    GroupPolicy = apps.get_model("accounts", "GroupPolicy")
    for policy in GroupPolicy.objects.select_related("group").all().iterator():
        if not policy.name:
            policy.name = policy.group.name
            policy.save(update_fields=("name",))


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_group_policy"),
    ]

    operations = [
        migrations.AddField(
            model_name="grouppolicy",
            name="name",
            field=models.CharField(default="", max_length=150),
        ),
        migrations.RunPython(copy_group_names_to_role_names, migrations.RunPython.noop),
    ]
