from django.db import models
from django.db.models import Q, Subquery

from accounts.models.role import Role


class EmployeeQuerySet(models.QuerySet):
    def visible_to(self, user, *, role_level=None):
        if not user or not user.is_authenticated:
            return self.none()
        if user.is_superuser:
            return self

        highest_role_scope = (
            Role.objects.filter(group__user__pk=user.pk)
            .order_by("-level")
            .values("scope")[:1]
        )
        employee_rows = list(
            self.model.objects.select_related("work_site")
            .annotate(_actor_role_scope=Subquery(highest_role_scope))
            .values(
                "id",
                "user_id",
                "manager_id",
                "work_site_id",
                "work_site__site_type",
                "work_site__parent_id",
                "_actor_role_scope",
            )
        )

        actor = next((row for row in employee_rows if row["user_id"] == user.pk), None)
        role_scope = (actor or {}).get("_actor_role_scope") or Role.Scope.SITE

        if role_scope == Role.Scope.COMPANY:
            return self

        if actor is None:
            return self.none()

        children = {}
        for row in employee_rows:
            if row["manager_id"] is not None:
                children.setdefault(row["manager_id"], []).append(row["id"])

        visible_ids = {actor["id"]}
        stack = [actor["id"]]
        while stack:
            manager_id = stack.pop()
            for child_id in children.get(manager_id, ()):
                if child_id not in visible_ids:
                    visible_ids.add(child_id)
                    stack.append(child_id)

        if actor["work_site_id"] is None:
            return self.filter(pk__in=visible_ids)

        if role_scope == Role.Scope.BRANCH:
            branch_id = (
                actor["work_site_id"]
                if actor["work_site__site_type"] == "branch"
                else actor["work_site__parent_id"]
            )
            if branch_id is None:
                return self.filter(pk=actor["id"])
            allowed_site_ids = {
                row["work_site_id"]
                for row in employee_rows
                if row["work_site_id"] == branch_id
                or row["work_site__parent_id"] == branch_id
            }
            visible_ids = {
                row["id"]
                for row in employee_rows
                if row["id"] in visible_ids and row["work_site_id"] in allowed_site_ids
            }
            return self.filter(pk__in=visible_ids)

        visible_ids = {
            row["id"]
            for row in employee_rows
            if row["id"] in visible_ids and row["work_site_id"] == actor["work_site_id"]
        }
        return self.filter(pk__in=visible_ids)
