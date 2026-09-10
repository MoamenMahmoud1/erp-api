"""Shared role fixtures for permission and employee visibility tests."""

from django.contrib.auth.models import Group, Permission

from accounts.models import GroupPolicy


def create_role(*, code, level, permissions=(), scope=GroupPolicy.Scope.SITE, requires_shift=False):
    group = Group.objects.create(name=f"Test {code.title()}")
    policy = GroupPolicy.objects.create(
        group=group,
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

    return policy
