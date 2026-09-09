from django.urls import path

from payments.api.views import CollectionView, RefundView, TransactionDetailView, TransactionListView

app_name = "payments"

urlpatterns = [
    path("collections/", CollectionView.as_view(), name="payment-collection"),
    path("refunds/", RefundView.as_view(), name="payment-refund"),
    path("transactions/", TransactionListView.as_view(), name="payment-transaction-list"),
    path("transactions/<int:pk>/", TransactionDetailView.as_view(), name="payment-transaction-detail"),
]
