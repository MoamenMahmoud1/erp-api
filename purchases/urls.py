from django.urls import path

from purchases.api.views import (
    PurchaseCancelView,
    PurchaseConfirmView,
    PurchaseDeleteView,
    PurchaseDetailView,
    PurchaseListCreateView,
    PurchaseReturnView,
    PurchaseUpdateView,
)

urlpatterns = [
    path("", PurchaseListCreateView.as_view(), name="purchase-list-create"),
    path("<int:pk>/", PurchaseDetailView.as_view(), name="purchase-detail"),
    path("<int:pk>/edit/", PurchaseUpdateView.as_view(), name="purchase-update"),
    path("<int:pk>/confirm/", PurchaseConfirmView.as_view(), name="purchase-confirm"),
    path("<int:pk>/cancel/", PurchaseCancelView.as_view(), name="purchase-cancel"),
    path("<int:pk>/delete/", PurchaseDeleteView.as_view(), name="purchase-delete"),
    path("<int:pk>/returns/", PurchaseReturnView.as_view(), name="purchase-return"),
]
