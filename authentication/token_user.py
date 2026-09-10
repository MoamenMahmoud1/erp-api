from rest_framework_simplejwt.models import TokenUser


class ERPTokenUser(TokenUser):
    """TokenUser hydrated from the active server-side Redis session snapshot."""

    def __init__(self, token, *, snapshot):
        super().__init__(token)
        self._snapshot = snapshot

    @property
    def username(self):
        return self._snapshot.get("username", "")

    @property
    def email(self):
        return self._snapshot.get("email", "")

    @property
    def first_name(self):
        return self._snapshot.get("first_name", "")

    @property
    def last_name(self):
        return self._snapshot.get("last_name", "")

    @property
    def is_active(self):
        return bool(self._snapshot.get("is_active", True))

    @property
    def is_staff(self):
        return bool(self._snapshot.get("is_staff", False))

    @property
    def is_superuser(self):
        return bool(self._snapshot.get("is_superuser", False))

    @property
    def role_level(self):
        try:
            return int(self._snapshot.get("role_level", 0))
        except (TypeError, ValueError):
            return 0

    @property
    def role_scope(self):
        value = self._snapshot.get("role_scope", "site")
        return value if value in {"company", "branch", "site"} else "site"

    @property
    def requires_shift(self):
        return bool(self._snapshot.get("requires_shift", False))

    @property
    def role(self):
        value = self._snapshot.get("role")
        return value if isinstance(value, dict) else None

    def get_all_permissions(self, obj=None):
        permissions = self._snapshot.get("permissions", ())
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

    @property
    def auth_session_snapshot(self):
        return self._snapshot
