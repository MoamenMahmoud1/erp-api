from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.balances import (
    customer_aging_view,
    customer_balances_view,
    supplier_aging_view,
    supplier_balances_view,
)
from accounting.api.statements import balance_sheet_view, cash_flow_view, profit_and_loss_view
from accounting.api.views import AccountViewSet, JournalEntryViewSet, general_ledger_view, trial_balance_view

router = DefaultRouter()
router.register("accounts", AccountViewSet, basename="account")
router.register("journal-entries", JournalEntryViewSet, basename="journal-entry")

urlpatterns = [
    path("", include(router.urls)),
    path("general-ledger/", general_ledger_view, name="general-ledger"),
    path("trial-balance/", trial_balance_view, name="trial-balance"),
    path("statements/profit-and-loss/", profit_and_loss_view, name="profit-and-loss"),
    path("statements/balance-sheet/", balance_sheet_view, name="balance-sheet"),
    path("statements/cash-flow/", cash_flow_view, name="cash-flow"),
    path("reports/customer-balances/", customer_balances_view, name="customer-balances"),
    path("reports/supplier-balances/", supplier_balances_view, name="supplier-balances"),
    path("reports/customer-aging/", customer_aging_view, name="customer-aging"),
    path("reports/supplier-aging/", supplier_aging_view, name="supplier-aging"),
]
