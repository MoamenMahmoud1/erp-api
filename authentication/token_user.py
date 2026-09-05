from rest_framework_simplejwt.models import TokenUser


class ERPTokenUser(TokenUser):
    """Stateless user backed only by trusted JWT claims."""

    @property
    def is_staff(self):
        return bool(self.token.get("is_staff", False))

    @property
    def is_superuser(self):
        return bool(self.token.get("is_superuser", False))

    @property
    def role_level(self):
        try:
            return int(self.token.get("role_level", 0))
        except (TypeError, ValueError):
            return 0

    def get_all_permissions(self, obj=None):
        permissions = self.token.get("permissions", ())
        if not isinstance(permissions, (list, tuple, set)):
            return set()
        return set(permissions)

    def get_user_permissions(self, obj=None):
        return self.get_all_permissions(obj)

    def get_group_permissions(self, obj=None):
        return self.get_all_permissions(obj)

    def has_perm(self, perm, obj=None):
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        return perm in self.get_all_permissions(obj)

    def has_perms(self, perm_list, obj=None):
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, module):
        prefix = f"{module}."
        return any(
            permission.startswith(prefix)
            for permission in self.get_all_permissions()
        )
