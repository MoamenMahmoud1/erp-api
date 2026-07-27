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
