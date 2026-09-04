from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from .views import health_live, health_ready, version_view

urlpatterns = [
    # Health / readiness probes (no auth, no secrets, must be fast).
    path("health/live/", health_live, name="health-live"),
    path("health/ready/", health_ready, name="health-ready"),
    path("api/v1/system/version/", version_view, name="system-version"),
    # OpenAPI schema + docs
    path(
        "api/v1/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),
    path(
        "api/v1/docs/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/docs/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("api/v1/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path(
        "api/v1/organization/",
        include(("organization.urls", "organization"), namespace="organization"),
    ),
    path("api/v1/", include(("customers.urls", "customers"), namespace="customers")),
    path("api/v1/", include(("products.urls", "products"), namespace="products")),
    path("api/v1/", include(("coupons.urls", "coupons"), namespace="coupons")),
    path("api/v1/", include(("invoices.urls", "invoices"), namespace="invoices")),
    path(
        "api/v1/payments/",
        include(("payments.urls", "payments"), namespace="payments"),
    ),
    path("api/v1/purchases/", include("purchases.urls"),),
    path("api/v1/suppliers/",include("suppliers.urls"),),
    path("admin/", admin.site.urls),
    #path("__debug__/", include("debug_toolbar.urls")),
]

if settings.DEBUG:
    if "silk" in settings.INSTALLED_APPS:
        urlpatterns.append(path("silk/", include("silk.urls", namespace="silk")))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,document_root=settings.STATIC_ROOT,)
