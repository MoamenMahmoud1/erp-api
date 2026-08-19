from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet

from common.permissions import ModelAccessPermission
from organization.api.serializers import SiteSerializer
from organization.models import Company, Site


class SiteViewSet(ModelViewSet):
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

    def perform_create(self, serializer):
        company = get_object_or_404(
            Company,
            singleton_marker=True,
        )
        serializer.save(company=company)
