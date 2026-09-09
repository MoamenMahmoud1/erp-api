from django.shortcuts import get_object_or_404
from rest_framework import viewsets

from common.permissions import ModelAccessPermission
from organization.api.serializers import DepartmentSerializer
from organization.models import Company, Department
from services.organization_scope import visible_site_ids


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.select_related("company", "site").order_by("code")
    serializer_class = DepartmentSerializer
    permission_classes = (ModelAccessPermission,)
    http_method_names = ("get", "post", "patch", "head", "options")

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset
        site_ids = visible_site_ids(user)
        if site_ids is None:
            return queryset
        return queryset.filter(site__isnull=True) | queryset.filter(site_id__in=site_ids)

    def perform_create(self, serializer):
        company = get_object_or_404(Company.objects.all(), singleton_marker=True)
        serializer.save(company=company)
