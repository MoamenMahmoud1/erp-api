from django.urls import path

from inventory.api.transfer_requests import (
    StockTransferRequestApproveView,
    StockTransferRequestListCreateView,
    StockTransferRequestRejectView,
    WarehouseManagerOptionsView,
)
from inventory.api.views import (
    LocationListView,
    MovementListView,
    StockBalanceListView,
    StockBatchBalanceListView,
    TransferView,
)

app_name = "inventory"

urlpatterns = [
    path("locations/", LocationListView.as_view(), name="locations"),
    path("stock/", StockBalanceListView.as_view(), name="stock"),
    path("batches/", StockBatchBalanceListView.as_view(), name="batches"),
    path("movements/", MovementListView.as_view(), name="movements"),
    path("transfers/", TransferView.as_view(), name="transfer"),
    path("warehouse-managers/", WarehouseManagerOptionsView.as_view(), name="warehouse-managers"),
    path("transfer-requests/", StockTransferRequestListCreateView.as_view(), name="transfer-requests"),
    path("transfer-requests/<int:pk>/approve/", StockTransferRequestApproveView.as_view(), name="transfer-request-approve"),
    path("transfer-requests/<int:pk>/reject/", StockTransferRequestRejectView.as_view(), name="transfer-request-reject"),
]
