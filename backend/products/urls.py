from django.urls import path

from .api.intelligence import product_intelligence_view
from .api.views import CartonPricingViewSet, ProductViewSet

app_name = "products"


product_list = ProductViewSet.as_view({"get": "list", "post": "create"})
product_detail = ProductViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
)
cartonpricing_list = CartonPricingViewSet.as_view({"get": "list", "post": "create"})
cartonpricing_detail = CartonPricingViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
)

urlpatterns = [
    path("intelligence/", product_intelligence_view, name="product-intelligence"),
    path("products/intelligence/", product_intelligence_view, name="product-intelligence-legacy"),
    path("carton-pricings/", cartonpricing_list, name="cartonpricing-list"),
    path("carton-pricings/<int:pk>/", cartonpricing_detail, name="cartonpricing-detail"),
    path("", product_list, name="product-list"),
    path("<int:pk>/", product_detail, name="product-detail"),
]
