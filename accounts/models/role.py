from django.contrib.auth.models import Group
from django.db import models

SUPERUSER_ROLE_LEVEL = 1000
GLOBAL_EMPLOYEE_VISIBILITY_LEVEL = 60


class Role(models.Model):
    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        related_name="role_profile",
    )
    code = models.SlugField(unique=True)
    level = models.PositiveSmallIntegerField(db_index=True)
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

        return (
            cls.objects.filter(group__user=user)
            .order_by("-level")
            .first()
        )

    @classmethod
    def level_for_user(cls, user):
        if not user or not user.is_authenticated:
            return 0
        if user.is_superuser:
            return SUPERUSER_ROLE_LEVEL

        role = cls.highest_for_user(user)
        return role.level if role else 0

    @classmethod
    def can_manage_user(cls, actor, target_user):
        if not actor or not actor.is_authenticated or not target_user:
            return False
        if actor.pk == target_user.pk:
            return True
        if actor.is_superuser:
            return True

        return cls.level_for_user(actor) > cls.level_for_user(target_user)
