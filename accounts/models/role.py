from django.contrib.auth.models import Group
from django.db import models
from django.db.models import IntegerField, Value
from django.db.models.functions import Coalesce


SUPERUSER_ROLE_LEVEL = 1000


class RoleProfile(models.Model):
    class Scope(models.TextChoices):
        COMPANY = "company", "Company"
        BRANCH = "branch", "Branch"
        SITE = "site", "Site"

    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="role_profile")
    name = models.CharField(max_length=150, default="")
    level = models.PositiveSmallIntegerField(default=0, db_index=True)
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.SITE, db_index=True)
    requires_shift = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-level", "name", "pk")
        verbose_name = "Role profile"
        verbose_name_plural = "Role profiles"

    def __str__(self):
        return self.name or self.group.name

    @classmethod
    def level_for_group(cls, group):
        if not group:
            return 0
        profile = getattr(group, "role_profile", None)
        return int(profile.level) if profile else 0

    @classmethod
    def scope_for_group(cls, group):
        if not group:
            return cls.Scope.SITE
        profile = getattr(group, "role_profile", None)
        return profile.scope if profile else cls.Scope.SITE

    @classmethod
    def requires_shift_for_group(cls, group):
        if not group:
            return False
        profile = getattr(group, "role_profile", None)
        return bool(profile and profile.requires_shift)

    @classmethod
    def name_for_group(cls, group):
        if not group:
            return ""
        profile = getattr(group, "role_profile", None)
        return (profile.name or group.name) if profile else group.name

    @classmethod
    def highest_for_user(cls, user):
        if not user or not user.is_authenticated:
            return None
        return (
            user.groups.select_related("role_profile")
            .annotate(
                _role_level=Coalesce(
                    "role_profile__level",
                    Value(0),
                    output_field=IntegerField(),
                )
            )
            .order_by("-_role_level", "role_profile__name", "name", "pk")
            .first()
        )

    @classmethod
    def level_for_user(cls, user):
        if not user or not user.is_authenticated:
            return 0
        if user.is_superuser:
            return SUPERUSER_ROLE_LEVEL
        token_role_level = getattr(user, "role_level", None)
        if token_role_level is not None:
            try:
                return int(token_role_level)
            except (TypeError, ValueError):
                pass
        return cls.level_for_group(cls.highest_for_user(user))

    @classmethod
    def highest_role_for_user(cls, user):
        return cls.highest_for_user(user)

    @classmethod
    def scope_for_user(cls, user):
        if user and user.is_superuser:
            return cls.Scope.COMPANY
        token_role_scope = getattr(user, "role_scope", None)
        if token_role_scope in {choice for choice, _label in cls.Scope.choices}:
            return token_role_scope
        return cls.scope_for_group(cls.highest_for_user(user))

    @classmethod
    def requires_shift_for_user(cls, user):
        if not user or user.is_superuser:
            return False
        token_requires_shift = getattr(user, "requires_shift", None)
        if token_requires_shift is not None:
            return bool(token_requires_shift)
        return cls.requires_shift_for_group(cls.highest_for_user(user))

    @classmethod
    def summary_for_user(cls, user):
        snapshot = getattr(user, "auth_session_snapshot", None)
        if isinstance(snapshot, dict) and isinstance(snapshot.get("role"), dict):
            return snapshot["role"]
        group = cls.highest_for_user(user)
        if group is None:
            return None
        profile = getattr(group, "role_profile", None)
        return {
            "id": group.pk,
            "name": cls.name_for_group(group),
            "level": cls.level_for_group(group),
            "scope": cls.scope_for_group(group),
            "requires_shift": cls.requires_shift_for_group(group),
            "description": profile.description if profile else "",
        }

    @classmethod
    def can_manage_user(cls, actor, target_user):
        if not actor or not actor.is_authenticated or not target_user:
            return False
        if actor.pk == target_user.pk or actor.is_superuser:
            return True
        return cls.level_for_user(actor) > cls.level_for_user(target_user)
