from adrf.routers import SimpleRouter

from .api.views import InvoiceViewSet

app_name = "invoices"

router = SimpleRouter()
router.register("invoices", InvoiceViewSet, basename="invoice")

urlpatterns = router.urls
