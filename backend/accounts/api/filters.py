from django.db.models import Q
from django_filters import rest_framework as filters

from accounts.models import Employee


class EmployeeFilter(filters.FilterSet):
    employee = filters.CharFilter(method="filter_employee")
    work_site = filters.NumberFilter(field_name="work_site_id")
    department = filters.NumberFilter(field_name="department_id")
    manager = filters.NumberFilter(field_name="manager_id")

    class Meta:
        model = Employee
        fields = ("employee", "work_site", "department", "manager")

    @staticmethod
    def filter_employee(queryset, name, value):
        value = value.strip()
        if not value:
            return queryset
        return queryset.filter(
            Q(user__username__icontains=value)
            | Q(user__email__icontains=value)
            | Q(user__first_name__icontains=value)
            | Q(user__last_name__icontains=value)
        ).distinct()
