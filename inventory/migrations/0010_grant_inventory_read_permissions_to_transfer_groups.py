from django.db import migrations


def grant_inventory_read_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    movement_content_type = ContentType.objects.get(
        app_label="inventory",
        model="stockmovement",
    )
    required_permissions = {
        permission.codename: permission
        for permission in Permission.objects.filter(
            content_type__app_label="inventory",
            codename__in=(
                "view_stocklocation",
                "view_stockbalance",
                "view_stockmovement",
            ),
        )
    }

    transfer_permission = Permission.objects.get(
        content_type=movement_content_type,
        codename="transfer_stock",
    )

    view_permissions = tuple(
        required_permissions[codename]
        for codename in (
            "view_stocklocation",
            "view_stockbalance",
            "view_stockmovement",
        )
        if codename in required_permissions
    )

    if not view_permissions:
        return

    for group in Group.objects.filter(permissions=transfer_permission).distinct():
        group.permissions.add(*view_permissions)


def noop(apps, schema_editor):
    # Do not remove read permissions on reverse: an administrator may have
    # granted them independently after the migration.
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0009_stock_valuation"),
    ]

    operations = [
        migrations.RunPython(grant_inventory_read_permissions, noop),
    ]
