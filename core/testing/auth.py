"""Authentication helpers for API tests.

Keep login endpoint coverage separate from protected-endpoint tests. Protected
API tests should construct the same stateful session primitives the production
login flow creates, without making every business test depend on login views.
"""

import uuid

from django.http import HttpResponse
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from authsession.cache import cache_active_session
from authsession.http import ClientContext, set_login_cookies
from authsession.models import AuthSession
from authsession.services import start_auth_session


STATEFUL_AUTH_COOKIES = ("refresh_token", "device_id")


def _assert_success(response, *, action: str):
    if not 200 <= response.status_code < 300:
        raise AssertionError(
            f"{action} failed with HTTP {response.status_code}: "
            f"{getattr(response, 'data', None)!r}"
        )


def _populate_auth_cache(*, user, access_token):
    access = AccessToken(access_token)
    session = AuthSession.objects.get(pk=access["sid"])
    cache_active_session(
        auth_session=session,
        user=user,
        access_token=access,
    )


def login_client(client: APIClient, *, user, password: str):
    """Log in through the real API and retain the returned browser cookies.

    Use this helper only when the login endpoint itself is part of the test.
    """
    csrf_response = client.get(reverse("accounts:csrf-token"))
    _assert_success(csrf_response, action="CSRF bootstrap")

    response = client.post(
        reverse("accounts:login"),
        {"identifier": user.email, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
    )
    _assert_success(response, action="login")

    for name in STATEFUL_AUTH_COOKIES:
        if name not in response.cookies:
            raise AssertionError(f"Login must set the {name} cookie")

    client.cookies.update(response.cookies)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    _populate_auth_cache(user=user, access_token=response.data["access"])
    return response


def authenticate_stateful_client(
    client: APIClient,
    *,
    user,
    device_id=None,
    device_name="Test device",
    user_agent="Test browser",
    ip_address="127.0.0.1",
):
    """Attach a valid access JWT and matching stateful auth cookies.

    This exercises the protected endpoint/session contract directly while
    leaving login endpoint coverage to ``login_client`` and its dedicated tests.
    The returned value is the persisted ``AuthSession`` model.
    """
    device_id = device_id or uuid.uuid4()
    client_context = ClientContext(
        device_id=device_id,
        device_name=device_name,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    session_result = start_auth_session(user=user, client_context=client_context)

    cookie_response = HttpResponse()
    set_login_cookies(
        cookie_response,
        refresh_token=session_result.refresh_token,
        device_id=session_result.device_id,
    )
    client.cookies.update(cookie_response.cookies)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {session_result.access_token}")
    _populate_auth_cache(user=user, access_token=session_result.access_token)
    return AuthSession.objects.get(pk=session_result.session_id)


def new_api_client() -> APIClient:
    """Return the default API client with CSRF enforcement enabled."""
    return APIClient(enforce_csrf_checks=True)
