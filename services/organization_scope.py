from django.db.models import Q, Subquery

from accounts.models import Employee


def visible_employee_user_ids(user):
    """User ids the actor may operate on, including the actor themself."""
    if not user or not user.is_authenticated:
        return Employee.objects.none().values("user_id")
    return Employee.objects.visible_to(user).values("user_id")


def visible_site_ids(user):
    """Return sites an employee can operate on, including child stores of a branch."""
    if not user or not user.is_authenticated:
        return Subquery(Employee.objects.none().values("work_site_id"))
    employee = getattr(user, "employee", None)
    if employee is None or employee.work_site_id is None:
        return None
    site = employee.work_site
    if site.site_type == "branch":
        from organization.models import Site
        return Subquery(Site.objects.filter(Q(pk=site.pk) | Q(parent_id=site.pk)).values("pk"))
    if site.site_type == "head_office":
        from organization.models import Site
        return Subquery(Site.objects.filter(company_id=site.company_id).values("pk"))
    return Subquery(Employee.objects.filter(pk=employee.pk).values("work_site_id"))


def filter_by_actor_scope(queryset, *, user, owner_field="created_by_id", site_field=None):
    """Scope records to the actor's employee tree and, when applicable, their site."""
    if not user or not user.is_authenticated:
        return queryset.none()
    if user.is_superuser:
        return queryset

    visible_ids = Subquery(visible_employee_user_ids(user))
    queryset = queryset.filter(Q(**{owner_field: user.pk}) | Q(**{f"{owner_field}__in": visible_ids}))

    if site_field:
        sites = visible_site_ids(user)
        if sites is not None:
            queryset = queryset.filter(**{f"{site_field}__in": sites})

    return queryset
