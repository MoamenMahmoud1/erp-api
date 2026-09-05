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
        return self.filter(Q(location_type="MAIN_WAREHOUSE") | Q(employee_id__in=employee_ids))

    def active(self):
        return self.filter(is_active=True)


class StockMovementQuerySet(models.QuerySet):
    def visible_to(self, user):
        if not user or not user.is_authenticated:
            return self.none()
        if user.is_superuser:
            return self
        employee_ids = Subquery(visible_employee_user_ids(user))
        return self.filter(
            Q(created_by_id__in=employee_ids)
            | Q(source_location__employee_id__in=employee_ids)
            | Q(destination_location__employee_id__in=employee_ids)
            | Q(source_location__location_type="MAIN_WAREHOUSE")
            | Q(destination_location__location_type="MAIN_WAREHOUSE")
        ).distinct()
