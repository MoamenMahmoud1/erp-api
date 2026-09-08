from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from common.pagination import StandardPagination
from accounts.api.serializers import EmployeeSerializer
from accounts.models import Employee
from accounts.permissions import EmployeeAccessPermission


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = (EmployeeAccessPermission,)
    pagination_class = StandardPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("work_site", "department", "manager")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    ordering_fields = ("user__username", "user__first_name", "created_at", "updated_at")
    ordering = ("user__username", "pk")

    def get_queryset(self):
        return (
            Employee.objects.visible_to(
                self.request.user,
                role_level=getattr(self.request, "_employee_role_level", None),
            )
            .select_related(
                "user",
                "manager",
                "manager__user",
                "work_site",
                "department",
            )
            .order_by(*self.ordering)
        )
