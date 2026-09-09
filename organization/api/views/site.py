from django.shortcuts import get_object_or_404
from rest_framework import viewsets

from common.permissions import ModelAccessPermission
from organization.api.serializers import SiteSerializer
from organization.models import Company, Site
from services.organization_scope import visible_site_ids


class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.select_related("company", "parent")
    serializer_class = SiteSerializer
    permission_classes = (ModelAccessPermission,)
    http_method_names = ("get", "post", "patch", "head", "options")

    def get_queryset(self):
        queryset = super().get_queryset()
        site_ids = visible_site_ids(self.request.user)
        if site_ids is None:
            return queryset
        return queryset.filter(pk__in=site_ids)

    def perform_create(self, serializer):
        company = get_object_or_404(Company.objects.all(), singleton_marker=True)
        serializer.save(company=company)
