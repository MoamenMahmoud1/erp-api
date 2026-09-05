"""Authentication helpers for API tests.

These helpers model the real browser flow: login returns an access token and
stateful refresh/device cookies, and protected stateful endpoints require all
three pieces of state.
"""

from django.urls import reverse
from rest_framework.test import APIClient


STATEFUL_AUTH_COOKIES = ("refresh_token", "device_id")


def _assert_success(response, *, action: str):
    if not 200 <= response.status_code < 300:
        raise AssertionError(
            f"{action} failed with HTTP {response.status_code}: "
            f"{getattr(response, 'data', None)!r}"
        )


def login_client(client: APIClient, *, user, password: str):
    """Log in through the real API and attach the stateful auth cookies."""
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
        cookie = response.cookies.get(name)
        if cookie is None:
            raise AssertionError(f"Login must set the {name} cookie")
        client.cookies.pop(name, None)
        client.cookies[name] = cookie.value

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return response


def new_api_client() -> APIClient:
    """Return the default API client with CSRF enforcement enabled."""
    return APIClient(enforce_csrf_checks=True)
