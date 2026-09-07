from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.analytics import (
    inventory_dashboard_view,
    purchase_dashboard_view,
    sales_by_employee_view,
    sales_dashboard_view,
    top_products_view,
)
from accounting.api.balances import (
    customer_aging_view,
    customer_balances_view,
    supplier_aging_view,
    supplier_balances_view,
)
from accounting.api.statements import balance_sheet_view, cash_flow_view, profit_and_loss_view
from accounting.api.views import (
    AccountViewSet,
    AccountingPeriodViewSet,
    ExpenseViewSet,
    JournalEntryViewSet,
    general_ledger_view,
    opening_balance_view,
    trial_balance_view,
)

router = DefaultRouter()
router.register("accounts", AccountViewSet, basename="account")
router.register("journal-entries", JournalEntryViewSet, basename="journal-entry")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("periods", AccountingPeriodViewSet, basename="accounting-period")

urlpatterns = [
    path("", include(router.urls)),
    path("general-ledger/", general_ledger_view, name="general-ledger"),
    path("trial-balance/", trial_balance_view, name="trial-balance"),
    path("opening-balance/", opening_balance_view, name="opening-balance"),
    path("statements/profit-and-loss/", profit_and_loss_view, name="profit-and-loss"),
    path("statements/balance-sheet/", balance_sheet_view, name="balance-sheet"),
    path("statements/cash-flow/", cash_flow_view, name="cash-flow"),
    path("reports/customer-balances/", customer_balances_view, name="customer-balances"),
    path("reports/supplier-balances/", supplier_balances_view, name="supplier-balances"),
    path("reports/customer-aging/", customer_aging_view, name="customer-aging"),
    path("reports/supplier-aging/", supplier_aging_view, name="supplier-aging"),
    path("analytics/sales/", sales_dashboard_view, name="analytics-sales"),
    path("analytics/purchases/", purchase_dashboard_view, name="analytics-purchases"),
    path("analytics/inventory/", inventory_dashboard_view, name="analytics-inventory"),
    path("analytics/top-products/", top_products_view, name="analytics-top-products"),
    path("analytics/sales-by-employee/", sales_by_employee_view, name="analytics-sales-by-employee"),
]
