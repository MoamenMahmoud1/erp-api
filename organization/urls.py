from django.urls import path
from rest_framework.routers import DefaultRouter

from organization.api.views import (
    CompanyDetailView,
    DepartmentViewSet,
    SiteViewSet,
)


app_name = "organization"

router = DefaultRouter()
router.register("sites", SiteViewSet, basename="site")
router.register(
    "departments",
    DepartmentViewSet,
    basename="department",
)

urlpatterns = [
    path(
        "company/",
        CompanyDetailView.as_view(),
        name="company-detail",
    ),
] + router.urls
