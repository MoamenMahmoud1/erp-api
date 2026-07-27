from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .views import version_view

urlpatterns = [
    path("api/v1/system/version/", version_view, name="system-version"),
    path("api/v1/", include("accounts.urls", namespace="accounts")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    if "silk" in settings.INSTALLED_APPS:
        urlpatterns.append(path("silk/", include("silk.urls", namespace="silk")))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
