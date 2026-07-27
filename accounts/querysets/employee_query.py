from django.db import models
from django.db.models.expressions import RawSQL

from accounts.models.role import GLOBAL_EMPLOYEE_VISIBILITY_LEVEL, Role


class EmployeeQuerySet(models.QuerySet):
    def visible_to(self, user):
        if not user or not user.is_authenticated:
            return self.none()

        if user.is_superuser:
            return self

        if Role.level_for_user(user) >= GLOBAL_EMPLOYEE_VISIBILITY_LEVEL:
            return self

        visible_employee_ids = RawSQL(
            """
            WITH RECURSIVE visible_employees(id) AS (
                SELECT id
                FROM accounts_employee
                WHERE user_id = %s
                UNION
                SELECT employee.id
                FROM accounts_employee AS employee
                INNER JOIN visible_employees AS visible
                    ON employee.manager_id = visible.id
            )
            SELECT id FROM visible_employees
            """,
            (user.pk,),
        )
        return self.filter(pk__in=visible_employee_ids)
