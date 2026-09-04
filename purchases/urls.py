from django.urls import path

from purchases.api.views import (
    PurchaseConfirmView,
    PurchaseDetailView,
    PurchaseListCreateView,
    PurchaseCancelView,
    PurchaseDeleteView,
)

urlpatterns = [
    path(
        "",
        PurchaseListCreateView.as_view(),
        name="purchase-list-create",
    ),
    path(
        "<int:pk>/",
        PurchaseDetailView.as_view(),
        name="purchase-detail",
    ),
    path(
        "<int:pk>/confirm/",
        PurchaseConfirmView.as_view(),
        name="purchase-confirm",
    ),
    path(
    "<int:pk>/cancel/",
    PurchaseCancelView.as_view(),
    name="purchase-cancel",
    ),
    path(
    "<int:pk>/delete/",
    PurchaseDeleteView.as_view(),
    name="purchase-delete",
    ),
]