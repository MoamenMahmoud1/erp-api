from rest_framework.permissions import BasePermission, DjangoModelPermissions


class ModelAccessPermission(DjangoModelPermissions):
    """Require the Django model permission for every API operation."""

    perms_map = {
        **DjangoModelPermissions.perms_map,
        "GET": [
            "%(app_label)s.view_%(model_name)s",
        ],
        "HEAD": [
            "%(app_label)s.view_%(model_name)s",
        ],
    }


class ReadAuthenticatedWriteStaffPermission(BasePermission):
    """Backward-compatible name for the strict model-permission policy."""

    def has_permission(self, request, view):
        return ModelAccessPermission().has_permission(request, view)
