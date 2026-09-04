from django.urls import path

from payments.api.views import CollectionView, TransactionListView

app_name = "payments"

urlpatterns = [
    path(
        "collections/",
        CollectionView.as_view(),
        name="payment-collection",
    ),
    path(
        "transactions/",
        TransactionListView.as_view(),
        name="payment-transaction-list",
    ),
]
