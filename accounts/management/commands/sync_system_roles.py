from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

from accounts.models import Role
from accounts.role_defaults import ROLE_DEFINITIONS


class Command(BaseCommand):
    help = "Create/update the standard ERP roles and assign their permissions."

    def handle(self, *args, **options):
        permission_cache = {}

        def permission(app_label, codename):
            key = (app_label, codename)
            if key not in permission_cache:
                try:
                    permission_cache[key] = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename,
                    )
                except Permission.DoesNotExist as exc:
                    raise CommandError(
                        f"Permission {app_label}.{codename} does not exist. Run migrate first."
                    ) from exc
            return permission_cache[key]

        for definition in ROLE_DEFINITIONS:
            group, _ = Group.objects.get_or_create(name=definition["name"])
            role, _ = Role.objects.update_or_create(
                code=definition["code"],
                defaults={
                    "group": group,
                    "level": definition["level"],
                    "scope": definition["scope"],
                    "requires_shift": definition["requires_shift"],
                    "is_system": True,
                    "description": f"System role: {definition['name']}",
                },
            )

            permissions = set()
            for permission_set in definition["permission_sets"]:
                kind, value = permission_set[0], permission_set[1]
                if kind == "all":
                    permissions.update(Permission.objects.all())
                    continue
                if kind == "app":
                    permissions.update(
                        Permission.objects.filter(content_type__app_label=value)
                    )
                    continue
                if kind == "permissions":
                    for app_label, codename in permission_set[1:]:
                        permissions.add(permission(app_label, codename))
                    continue
                raise CommandError(f"Unknown role permission set: {kind}")

            group.permissions.set(permissions)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Synced {role.code}: scope={role.scope}, shift={role.requires_shift}, permissions={len(permissions)}"
                )
            )
