"""Core middleware: proxy trusted headers + request correlation IDs."""

import logging
import re
import time
import uuid
from contextvars import ContextVar

from django.conf import settings

from core.proxy import is_trusted_proxy, normalize_ip

CORRELATION_HEADER = "HTTP_X_REQUEST_ID"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_current_request_id: ContextVar[str | None] = ContextVar("erp_request_id", default=None)


def get_current_request_id() -> str | None:
    return _current_request_id.get()


class _RequestIdLogRecordFactory:
    def __init__(self, factory):
        self._factory = factory

    def __call__(self, *args, **kwargs):
        record = self._factory(*args, **kwargs)
        record.request_id = get_current_request_id() or "-"
        return record


logging.setLogRecordFactory(_RequestIdLogRecordFactory(logging.getLogRecordFactory()))


class RequestCorrelationMiddleware:
    response_header = "X-Request-Id"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied_request_id = request.META.get(CORRELATION_HEADER, "")
        request_id = supplied_request_id if _REQUEST_ID_PATTERN.fullmatch(supplied_request_id) else uuid.uuid4().hex
        request.META[CORRELATION_HEADER] = request_id
        token = _current_request_id.set(request_id)
        started = time.perf_counter()
        try:
            response = self.get_response(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logging.getLogger("erp.metrics").info(
                "request method=%s path=%s status=500 duration_ms=%.2f",
                request.method,
                request.path,
                elapsed_ms,
            )
            raise
        else:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logging.getLogger("erp.metrics").info(
                "request method=%s path=%s status=%s duration_ms=%.2f",
                request.method,
                request.path,
                response.status_code,
                elapsed_ms,
            )
            response[self.response_header] = request_id
            return response
        finally:
            _current_request_id.reset(token)


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

    def _strip_headers(self, request):
        remote_address = normalize_ip(request.META.get("REMOTE_ADDR"))
        trust_headers = (
            getattr(settings, "TRUST_PROXY_HEADERS", False)
            and remote_address is not None
            and is_trusted_proxy(remote_address)
        )
        if not trust_headers:
            for header in self.forwarded_headers:
                request.META.pop(header, None)

    def __call__(self, request):
        self._strip_headers(request)
        return self.get_response(request)
