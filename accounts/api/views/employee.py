from rest_framework.viewsets import ModelViewSet
from accounts.api.serializers import EmployeeSerializer
from accounts.models import Employee
from accounts.permissions import EmployeeAccessPermission


class EmployeeViewSet(ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = (EmployeeAccessPermission,)

    def get_queryset(self):
        return (
            Employee.objects.visible_to(self.request.user)
            .select_related("user")
            .order_by("pk")
        )
