from adrf import viewsets
from adrf.shortcuts import aget_object_or_404

from common.permissions import ModelAccessPermission
from organization.api.serializers import DepartmentSerializer
from organization.models import Company, Department


class DepartmentViewSet(viewsets.ModelViewSet):
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

    async def perform_acreate(self, serializer):
        company = await aget_object_or_404(
            Company.objects.all(),
            singleton_marker=True,
        )
        await serializer.asave(company=company)
