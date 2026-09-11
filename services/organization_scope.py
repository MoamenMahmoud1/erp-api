from django.db.models import Q, Subquery

from accounts.models import Employee, RoleProfile


def visible_employee_user_ids(user):
    """User ids the actor may operate on, including the actor themself."""
    if not user or not user.is_authenticated:
        return Employee.objects.none().values("user_id")
    return Employee.objects.visible_to(user).values("user_id")


def visible_site_ids(user):
    """Return the site ids an actor may access from their role scope."""
    if not user or not user.is_authenticated or user.is_superuser:
        return None

    role_scope = RoleProfile.scope_for_user(user)
    if role_scope == RoleProfile.Scope.COMPANY:
        return None

    employee = getattr(user, "employee", None)
    if employee is None or employee.work_site_id is None:
        return Subquery(Employee.objects.none().values("work_site_id"))

    from organization.models import Site

    site = employee.work_site
    if role_scope == RoleProfile.Scope.BRANCH:
        branch_id = site.pk if site.site_type == Site.Type.BRANCH else site.parent_id
        if branch_id is None:
            return Subquery(Site.objects.filter(pk=site.pk).values("pk"))
        return Subquery(
            Site.objects.filter(Q(pk=branch_id) | Q(parent_id=branch_id)).values("pk")
        )

    return Subquery(Site.objects.filter(pk=site.pk).values("pk"))


def filter_by_actor_scope(queryset, *, user, owner_field="created_by_id", site_field=None):
    """Scope records by company/branch/site role scope and actor ownership.

    Explicit ownership is retained for legacy rows that predate site assignment;
    this never grants access to another user's site-bound row.
    """
    if not user or not user.is_authenticated:
        return queryset.none()
    if user.is_superuser:
        return queryset

    role_scope = RoleProfile.scope_for_user(user)
    if site_field and role_scope != RoleProfile.Scope.COMPANY:
        sites = visible_site_ids(user)
        if sites is None:
            return queryset
        legacy_owned = Q(**{f"{site_field}__isnull": True}) & Q(**{owner_field: user.pk})
        return queryset.filter(
            legacy_owned | Q(**{f"{site_field}__in": sites})
        )

    visible_ids = Subquery(visible_employee_user_ids(user))
    return queryset.filter(
        Q(**{owner_field: user.pk})
        | Q(**{f"{owner_field}__in": visible_ids})
    )
