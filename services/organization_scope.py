from django.db.models import Q, Subquery

from accounts.models import Employee


def visible_employee_user_ids(user):
    """User ids the actor may operate on, including the actor themself."""
    if not user or not user.is_authenticated:
        return Employee.objects.none().values("user_id")
    return Employee.objects.visible_to(user).values("user_id")


def filter_by_actor_scope(queryset, *, user, owner_field="created_by_id"):
    """Scope records to the actor and any employees visible in their tree."""
    if not user or not user.is_authenticated:
        return queryset.none()
    if user.is_superuser:
        return queryset
    visible_ids = Subquery(visible_employee_user_ids(user))
    return queryset.filter(Q(**{owner_field: user.pk}) | Q(**{f"{owner_field}__in": visible_ids}))
