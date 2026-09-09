from django.db import models
from django.db.models import Q, Subquery

from services.organization_scope import visible_employee_user_ids


class StockLocationQuerySet(models.QuerySet):
    def visible_to(self, user):
        if not user or not user.is_authenticated:
            return self.none()
        if user.is_superuser:
            return self

        employee_ids = Subquery(visible_employee_user_ids(user))
        employee = getattr(user, "employee", None)
        if employee and employee.work_site_id:
            from services.organization_scope import visible_site_ids
            site_ids = visible_site_ids(user)
            return self.filter(site_id__in=site_ids)

        return self.filter(Q(employee_id=user.pk) | Q(employee_id__in=employee_ids))

    def active(self):
        return self.filter(is_active=True)


class StockMovementQuerySet(models.QuerySet):
    def visible_to(self, user):
        if not user or not user.is_authenticated:
            return self.none()
        if user.is_superuser:
            return self

        employee_ids = Subquery(visible_employee_user_ids(user))
        employee = getattr(user, "employee", None)
        if employee and employee.work_site_id:
            from services.organization_scope import visible_site_ids
            site_ids = visible_site_ids(user)
            return self.filter(
                Q(source_location__site_id__in=site_ids)
                | Q(destination_location__site_id__in=site_ids)
            ).distinct()

        return self.filter(
            Q(created_by_id=user.pk)
            | Q(created_by_id__in=employee_ids)
            | Q(source_location__employee_id=user.pk)
            | Q(destination_location__employee_id=user.pk)
            | Q(source_location__employee_id__in=employee_ids)
            | Q(destination_location__employee_id__in=employee_ids)
        ).distinct()
