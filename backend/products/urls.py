from django.urls import path
from rest_framework.routers import SimpleRouter

from .api.intelligence import product_intelligence_view
from .api.views import CartonPricingViewSet, ProductViewSet

app_name = "products"

router = SimpleRouter()
router.register("", ProductViewSet, basename="product")
router.register("carton-pricings", CartonPricingViewSet, basename="cartonpricing")

urlpatterns = [
    path("intelligence/", product_intelligence_view, name="product-intelligence"),
    path("products/intelligence/", product_intelligence_view, name="product-intelligence-legacy"),
    path("intelligence/", product_intelligence_view, name="product-intelligence-legacy"),
    *router.urls,
]
