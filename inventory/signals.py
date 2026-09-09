from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver


INVENTORY_READ_CODENAMES = (
    "view_stocklocation",
    "view_stockbalance",
    "view_stockmovement",
)


@receiver(post_migrate)
def grant_inventory_read_permissions_after_migrate(sender, app_config, **kwargs):
    """Grant inventory read access after Django creates ContentTypes/Permissions."""
    if app_config and app_config.label != "inventory":
        return

    transfer_permission = Permission.objects.filter(
        content_type__app_label="inventory",
        codename="transfer_stock",
    ).first()
    if transfer_permission is None:
        return

    view_permissions = list(
        Permission.objects.filter(
            content_type__app_label="inventory",
            codename__in=INVENTORY_READ_CODENAMES,
        )
    )
    if not view_permissions:
        return

    transfer_groups = Group.objects.filter(permissions=transfer_permission).distinct()
    for group in transfer_groups:
        group.permissions.add(*view_permissions)
