from django.shortcuts import get_object_or_404
from rest_framework.generics import RetrieveUpdateAPIView

from common.permissions import ModelAccessPermission
from organization.api.serializers import CompanySerializer
from organization.models import Company


class CompanyDetailView(RetrieveUpdateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = (ModelAccessPermission,)
    http_method_names = (
        "get",
        "patch",
        "head",
        "options",
    )

    def get_object(self):
        company = get_object_or_404(
            self.get_queryset(),
            singleton_marker=True,
        )
        self.check_object_permissions(
            self.request,
            company,
        )
        return company