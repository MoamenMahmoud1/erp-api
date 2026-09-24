from rest_framework.routers import SimpleRouter

from .api.views import CustomerViewSet

app_name = "customers"

router = SimpleRouter()
router.register("", CustomerViewSet, basename="customer")

urlpatterns = router.urls
