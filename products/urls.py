from rest_framework.routers import SimpleRouter

from .api.views import CartonPricingViewSet, ProductViewSet

app_name = "products"

router = SimpleRouter()
router.register("products", ProductViewSet, basename="product")
router.register("carton-pricings", CartonPricingViewSet, basename="cartonpricing")

urlpatterns = router.urls