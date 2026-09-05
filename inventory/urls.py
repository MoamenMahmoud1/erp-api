from django.urls import path

from inventory.api.views import LocationListView, MovementListView, StockBalanceListView, TransferView

app_name = "inventory"

urlpatterns = [
    path("locations/", LocationListView.as_view(), name="locations"),
    path("stock/", StockBalanceListView.as_view(), name="stock"),
    path("movements/", MovementListView.as_view(), name="movements"),
    path("transfers/", TransferView.as_view(), name="transfer"),
]
