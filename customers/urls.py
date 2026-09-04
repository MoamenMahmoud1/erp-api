from adrf.routers import SimpleRouter

from .api.views import CustomerViewSet

app_name = "customers"

router = SimpleRouter()
router.register("customers", CustomerViewSet, basename="customer")

urlpatterns = router.urls
