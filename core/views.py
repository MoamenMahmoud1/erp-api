from django.http import JsonResponse

from django.db import connection

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
    """Liveness probe: process is alive and can respond.

    Deliberately does NOT depend on external services so load balancers / k8s
    can distinguish "process running" from "dependencies unavailable".
    """
    return JsonResponse({"status": "ok"})


def health_ready(request):
    """Readiness probe: required dependencies (database) are reachable.

    A failed DB connection is surfaced as 503. No secrets or stack traces are
    ever returned.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable", "db": "down"}, status=503)

    return JsonResponse({"status": "ok", "db": "up"})
