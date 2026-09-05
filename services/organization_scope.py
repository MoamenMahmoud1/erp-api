from django.db.models import Subquery

from accounts.models import Employee


def visible_employee_user_ids(user):
    """Return authenticated user ids visible to the actor's employee scope."""
    return Employee.objects.visible_to(user).values("user_id")


def filter_by_actor_scope(queryset, *, user, owner_field="created_by_id"):
    """Restrict a queryset to records owned by the actor or visible team members."""
    return queryset.filter(**{f"{owner_field}__in": Subquery(visible_employee_user_ids(user))})
