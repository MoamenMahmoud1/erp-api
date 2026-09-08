from rest_framework.permissions import BasePermission, DjangoModelPermissions


class ModelAccessPermission(DjangoModelPermissions):
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
    """Compatibility permission with explicit model permissions for writes."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        model = view.get_queryset().model
        action = getattr(view, "action", None)
        permission_map = {
            "create": f"{model._meta.app_label}.add_{model._meta.model_name}",
            "acreate": f"{model._meta.app_label}.add_{model._meta.model_name}",
            "update": f"{model._meta.app_label}.change_{model._meta.model_name}",
            "aupdate": f"{model._meta.app_label}.change_{model._meta.model_name}",
            "partial_update": f"{model._meta.app_label}.change_{model._meta.model_name}",
            "partial_aupdate": f"{model._meta.app_label}.change_{model._meta.model_name}",
            "destroy": f"{model._meta.app_label}.delete_{model._meta.model_name}",
            "adestroy": f"{model._meta.app_label}.delete_{model._meta.model_name}",
        }
        codename = permission_map.get(action)
        if codename is None:
            return False
        return user.has_perm(codename)
