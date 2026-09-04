"""Core middleware: proxy trusted headers + request correlation IDs."""
import logging
import uuid
from contextvars import ContextVar
from inspect import iscoroutinefunction, markcoroutinefunction

from django.conf import settings

from core.proxy import is_trusted_proxy, normalize_ip

CORRELATION_HEADER = "HTTP_X_REQUEST_ID"

_current_request_id: ContextVar[str | None] = ContextVar(
    "erp_request_id", default=None
)


def get_current_request_id() -> str | None:
    """Return the request id of the current request (or ``None``)."""
    return _current_request_id.get()


class _RequestIdFilter(logging.Filter):
    """Add ``request_id`` to every log record for structured formatters."""

    def filter(self, record):
        record.request_id = get_current_request_id() or "-"
        return True


class _RequestIdLogRecordFactory:
    """Wrap the default LogRecord factory to inject ``request_id``."""

    def __init__(self, factory):
        self._factory = factory

    def __call__(self, *args, **kwargs):
        record = self._factory(*args, **kwargs)
        record.request_id = get_current_request_id() or "-"
        return record


logging.setLogRecordFactory(
    _RequestIdLogRecordFactory(logging.getLogRecordFactory())
)


class RequestCorrelationMiddleware:
    """Hybrid middleware that preserves the ASGI async path without adaptation."""

    response_header = "X-Request-Id"
    async_capable = True
    sync_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        self._is_async = iscoroutinefunction(get_response)
        if self._is_async:
            markcoroutinefunction(self)

    def __call__(self, request):
        if self._is_async:
            return self._async_call(request)

        request_id = request.META.get(CORRELATION_HEADER) or uuid.uuid4().hex
        request.META[CORRELATION_HEADER] = request_id
        token = _current_request_id.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            _current_request_id.reset(token)
        response[self.response_header] = request_id
        return response

    async def _async_call(self, request):
        request_id = request.META.get(CORRELATION_HEADER) or uuid.uuid4().hex
        request.META[CORRELATION_HEADER] = request_id
        token = _current_request_id.set(request_id)
        try:
            response = await self.get_response(request)
        finally:
            _current_request_id.reset(token)
        response[self.response_header] = request_id
        return response


class TrustedProxyHeadersMiddleware:
    """Hybrid middleware that normalizes forwarded headers without sync adaptation."""

    forwarded_headers = (
        "HTTP_FORWARDED",
        "HTTP_X_FORWARDED_FOR",
        "HTTP_X_FORWARDED_HOST",
        "HTTP_X_FORWARDED_PORT",
        "HTTP_X_FORWARDED_PROTO",
    )

    async_capable = True
    sync_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        self._is_async = iscoroutinefunction(get_response)
        if self._is_async:
            markcoroutinefunction(self)

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
        if self._is_async:
            return self._async_call(request)
        self._strip_headers(request)
        return self.get_response(request)

    async def _async_call(self, request):
        self._strip_headers(request)
        return await self.get_response(request)
