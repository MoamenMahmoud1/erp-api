from django.urls import path

from suppliers.api.views import (
    SupplierDetailView,
    SupplierListCreateView,
)

urlpatterns = [
    path(
        "",
        SupplierListCreateView.as_view(),
        name="supplier-list-create",
    ),
    path(
        "<int:pk>/",
        SupplierDetailView.as_view(),
        name="supplier-detail",
    ),
]