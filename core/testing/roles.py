"""Shared role fixtures for permission and employee visibility tests."""

from django.contrib.auth.models import Group, Permission

from accounts.models import Role


def create_role(*, code, level, permissions=(), scope=Role.Scope.SITE, requires_shift=False):
    group = Group.objects.create(name=f"Test {code.title()}")
    role = Role.objects.create(
        group=group,
        code=code,
        level=level,
        scope=scope,
        requires_shift=requires_shift,
    )

    if permissions:
        group.permissions.set(
            Permission.objects.filter(
                content_type__app_label="accounts",
                content_type__model="employee",
                codename__in=permissions,
            )
        )

    return role
