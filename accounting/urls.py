from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.views import AccountViewSet, JournalEntryViewSet, general_ledger_view, trial_balance_view

router = DefaultRouter()
router.register("accounts", AccountViewSet, basename="account")
router.register("journal-entries", JournalEntryViewSet, basename="journal-entry")

urlpatterns = [
    path("", include(router.urls)),
    path("general-ledger/", general_ledger_view, name="general-ledger"),
    path("trial-balance/", trial_balance_view, name="trial-balance"),
]
