from adrf import viewsets
from adrf.shortcuts import aget_object_or_404

from common.permissions import ModelAccessPermission
from organization.api.serializers import SiteSerializer
from organization.models import Company, Site


class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.select_related(
        "company",
        "parent",
    )
    serializer_class = SiteSerializer
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
