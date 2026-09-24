from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse

from .version import API_VERSION, __version__


def version_view(request):
    return JsonResponse(
        {
            "name": "apihigh-erp",
            "version": __version__,
            "api_version": API_VERSION,
        }
    )


def health_live(request):
    """Liveness probe: process is alive and can respond."""
    return JsonResponse({"status": "ok"})


def health_ready(request):
    """Readiness probe for the database and configured cache backend."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable", "db": "down"}, status=503)

    try:
        probe_key = "erp:health:cache"
        cache.set(probe_key, "ok", 10)
        if cache.get(probe_key) != "ok":
            raise RuntimeError("cache probe failed")
    except Exception:
        return JsonResponse({"status": "unavailable", "db": "up", "cache": "down"}, status=503)

    return JsonResponse({"status": "ok", "db": "up", "cache": "up"})
