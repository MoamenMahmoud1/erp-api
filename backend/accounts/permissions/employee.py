from rest_framework.permissions import BasePermission

from accounts.models import RoleProfile


class EmployeeAccessPermission(BasePermission):
    permission_map = {
        "list": "accounts.view_employee",
        "alist": "accounts.view_employee",
        "retrieve": "accounts.view_employee",
        "aretrieve": "accounts.view_employee",
        "options": "accounts.add_employee",
        "aoptions": "accounts.add_employee",
        "create": "accounts.add_employee",
        "acreate": "accounts.add_employee",
        "update": "accounts.change_employee",
        "aupdate": "accounts.change_employee",
        "partial_update": "accounts.change_employee",
        "partial_aupdate": "accounts.change_employee",
        "destroy": "accounts.delete_employee",
        "adestroy": "accounts.delete_employee",
        "groups": "accounts.view_employee",
        "agroups": "accounts.view_employee",
    }

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        request._employee_role_level = RoleProfile.level_for_user(request.user)

        action = getattr(view, "action", None)
        codename = self.permission_map.get(action)
        if not codename:
            return False

        return request.user.has_perm(codename)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        if getattr(view, "action", None) in {
            "update",
            "aupdate",
            "partial_update",
            "partial_aupdate",
            "destroy",
            "adestroy",
        }:
            return RoleProfile.can_manage_user(request.user, obj.user)

        return True
