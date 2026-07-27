import uuid
from dataclasses import dataclass

from django.conf import settings
from django.utils.cache import patch_cache_control
from rest_framework_simplejwt.settings import api_settings

from core.proxy import is_trusted_proxy, normalize_ip


DEVICE_COOKIE_NAME = "device_id"
DEVICE_COOKIE_SALT = "accounts.auth-device"
DEVICE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
AUTH_COOKIE_PATH = "/api/v1/auth/"


@dataclass(frozen=True, slots=True)
class ClientContext:
    device_id: uuid.UUID
    device_name: str
    user_agent: str
    ip_address: str | None


def get_device_id(request):
    cookie_value = request.get_signed_cookie(
        DEVICE_COOKIE_NAME,
        default=None,
        salt=DEVICE_COOKIE_SALT,
        max_age=DEVICE_COOKIE_MAX_AGE,
    )

    try:
        return uuid.UUID(cookie_value)
    except (TypeError, ValueError):
        return None


def get_client_ip(request):
    remote_address = normalize_ip(request.META.get("REMOTE_ADDR"))
    if remote_address is None or not is_trusted_proxy(remote_address):
        return remote_address

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    forwarded_chain = [
        normalize_ip(value.strip())
        for value in forwarded_for.split(",")
        if value.strip()
    ]
    if not forwarded_chain or any(value is None for value in forwarded_chain):
        return remote_address

    address_chain = [*forwarded_chain, remote_address]
    while len(address_chain) > 1 and is_trusted_proxy(address_chain[-1]):
        address_chain.pop()
    return address_chain[-1]


def get_client_context(request, *, device_id=None):
    return ClientContext(
        device_id=device_id or get_device_id(request) or uuid.uuid4(),
        device_name=request.headers.get("X-Device-Name", "")[:100],
        user_agent=request.headers.get("User-Agent", "")[:1000],
        ip_address=get_client_ip(request),
    )


def _cookie_options():
    return {
        "httponly": True,
        "secure": not settings.DEBUG,
        "samesite": "Lax",
        "path": AUTH_COOKIE_PATH,
    }


def set_refresh_cookie(response, *, refresh_token, max_age=None):
    if max_age is None:
        max_age = int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds())

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=max_age,
        **_cookie_options(),
    )


def set_login_cookies(
    response,
    *,
    refresh_token,
    device_id,
):
    set_refresh_cookie(
        response,
        refresh_token=refresh_token,
    )
    response.set_signed_cookie(
        key=DEVICE_COOKIE_NAME,
        value=str(device_id),
        salt=DEVICE_COOKIE_SALT,
        max_age=DEVICE_COOKIE_MAX_AGE,
        **_cookie_options(),
    )


def clear_login_cookies(response):
    for cookie_name in ("refresh_token", DEVICE_COOKIE_NAME):
        response.delete_cookie(
            key=cookie_name,
            path=AUTH_COOKIE_PATH,
            samesite="lax",
        )


def prevent_response_caching(response):
    patch_cache_control(response, no_store=True, private=True)
    response["Pragma"] = "no-cache"


class NoStoreResponseMixin:
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        prevent_response_caching(response)
        return response
