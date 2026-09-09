from django.db import models
from django.db.models import Q, Subquery

from accounts.models.role import Role


class EmployeeQuerySet(models.QuerySet):
    def visible_to(self, user, *, role_level=None):
        if not user or not user.is_authenticated:
            return self.none()
        if user.is_superuser:
            return self

        role_scope = Role.scope_for_user(user)
        if role_scope == Role.Scope.COMPANY:
            return self

        employee = getattr(user, "employee", None)
        if employee is None or employee.work_site_id is None:
            return self.filter(user_id=user.pk)

        if role_scope == Role.Scope.BRANCH:
            return self.filter(
                Q(work_site_id=employee.work_site_id)
                | Q(work_site__parent_id=employee.work_site_id)
            )

        employee_ids = Subquery(
            self.model.objects.filter(user_id=user.pk).values("pk")
        )
        return self.filter(pk=employee_ids)
