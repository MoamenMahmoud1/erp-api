from django.conf import settings

from core.proxy import is_trusted_proxy, normalize_ip


class TrustedProxyHeadersMiddleware:
    forwarded_headers = (
        "HTTP_FORWARDED",
        "HTTP_X_FORWARDED_FOR",
        "HTTP_X_FORWARDED_HOST",
        "HTTP_X_FORWARDED_PORT",
        "HTTP_X_FORWARDED_PROTO",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        remote_address = normalize_ip(request.META.get("REMOTE_ADDR"))
        trust_headers = (
            getattr(settings, "TRUST_PROXY_HEADERS", False)
            and remote_address is not None
            and is_trusted_proxy(remote_address)
        )
        if not trust_headers:
            for header in self.forwarded_headers:
                request.META.pop(header, None)

        return self.get_response(request)
