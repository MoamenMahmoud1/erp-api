from django.contrib.auth.models import Group
from django.db import models

SUPERUSER_ROLE_LEVEL = 1000
GLOBAL_EMPLOYEE_VISIBILITY_LEVEL = 60


class Role(models.Model):
    class Scope(models.TextChoices):
        COMPANY = "company", "Company"
        BRANCH = "branch", "Branch"
        SITE = "site", "Site"

    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="role_profile")
    code = models.SlugField(unique=True)
    level = models.PositiveSmallIntegerField(db_index=True)
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.SITE, db_index=True)
    requires_shift = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-level", "code")

    def __str__(self):
        return f"{self.group.name} ({self.level})"

    @classmethod
    def highest_for_user(cls, user):
        if not user or not user.is_authenticated:
            return None
        return cls.objects.filter(group__user=user).order_by("-level").first()

    @classmethod
    def level_for_user(cls, user):
        if not user or not user.is_authenticated:
            return 0
        if user.is_superuser:
            return SUPERUSER_ROLE_LEVEL
        token_role_level = getattr(user, "role_level", None)
        if token_role_level is not None:
            return int(token_role_level)
        role = cls.highest_for_user(user)
        return role.level if role else 0

    @classmethod
    def highest_role_for_user(cls, user):
        if not user or not user.is_authenticated:
            return None
        return cls.highest_for_user(user)

    @classmethod
    def scope_for_user(cls, user):
        if user and user.is_superuser:
            return cls.Scope.COMPANY
        role = cls.highest_for_user(user)
        return role.scope if role else cls.Scope.SITE

    @classmethod
    def requires_shift_for_user(cls, user):
        if not user or user.is_superuser:
            return False
        role = cls.highest_for_user(user)
        return bool(role and role.requires_shift)

    @classmethod
    def can_manage_user(cls, actor, target_user):
        if not actor or not actor.is_authenticated or not target_user:
            return False
        if actor.pk == target_user.pk or actor.is_superuser:
            return True
        return cls.level_for_user(actor) > cls.level_for_user(target_user)
