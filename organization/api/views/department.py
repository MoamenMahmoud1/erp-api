from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet

from common.permissions import ModelAccessPermission
from organization.api.serializers import DepartmentSerializer
from organization.models import Company, Department


class DepartmentViewSet(ModelViewSet):
    queryset = Department.objects.select_related(
        "company",
        "site",
    ).order_by("code")
    serializer_class = DepartmentSerializer
    permission_classes = (ModelAccessPermission,)
    http_method_names = (
        "get",
        "post",
        "patch",
        "head",
        "options",
    )

    def perform_create(self, serializer):
        company = get_object_or_404(
            Company.objects.all(),
            singleton_marker=True,
        )
        serializer.save(company=company)
