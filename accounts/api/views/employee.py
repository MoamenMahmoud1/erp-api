from adrf import viewsets
from accounts.api.serializers import EmployeeSerializer
from accounts.models import Employee
from accounts.permissions import EmployeeAccessPermission


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = (EmployeeAccessPermission,)

    def get_queryset(self):
        return (
            Employee.objects.visible_to(
                self.request.user,
                role_level=getattr(self.request, "_employee_role_level", None),
            )
            .select_related("user")
            .order_by("pk")
        )
