import uuid

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from authsession.http import (
    DEVICE_COOKIE_NAME,
    DEVICE_COOKIE_SALT,
    get_client_context,
    get_client_ip,
    get_device_id,
    clear_login_cookies,
    prevent_response_caching,
    set_login_cookies,
    set_refresh_cookie,
)
from core.middleware import TrustedProxyHeadersMiddleware


class AuthenticationHttpTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_new_client_context_has_device_id_and_sanitized_metadata(self):
        request = self.factory.get(
            "/api/v1/auth/csrf/",
            HTTP_X_DEVICE_NAME="A" * 120,
            HTTP_USER_AGENT="B" * 1200,
            REMOTE_ADDR="192.0.2.10",
        )

        context = get_client_context(request)

        self.assertIsInstance(context.device_id, uuid.UUID)
        self.assertEqual(context.device_name, "A" * 100)
        self.assertEqual(context.user_agent, "B" * 1000)
        self.assertEqual(context.ip_address, "192.0.2.10")

    def test_existing_signed_device_cookie_is_reused(self):
        device_id = uuid.uuid4()
        cookie_response = HttpResponse()
        cookie_response.set_signed_cookie(
            DEVICE_COOKIE_NAME,
            str(device_id),
            salt=DEVICE_COOKIE_SALT,
        )
        request = self.factory.get("/api/v1/auth/csrf/")
        request.COOKIES[DEVICE_COOKIE_NAME] = cookie_response.cookies[
            DEVICE_COOKIE_NAME
        ].value

        context = get_client_context(request)

        self.assertEqual(context.device_id, device_id)

    def test_missing_device_cookie_has_no_existing_device(self):
        request = self.factory.get("/api/v1/auth/refresh/")

        self.assertIsNone(get_device_id(request))

    def test_invalid_ip_is_not_stored(self):
        request = self.factory.get(
            "/api/v1/auth/csrf/",
            REMOTE_ADDR="not-an-ip",
        )

        context = get_client_context(request)

        self.assertIsNone(context.ip_address)

    @override_settings(TRUSTED_PROXY_IPS=())
    def test_untrusted_peer_cannot_spoof_forwarded_ip(self):
        request = self.factory.get(
            "/api/v1/auth/login/",
            REMOTE_ADDR="198.51.100.8",
            HTTP_X_FORWARDED_FOR="203.0.113.9",
        )

        self.assertEqual(get_client_ip(request), "198.51.100.8")

    @override_settings(TRUSTED_PROXY_IPS=("10.0.0.0/8",))
    def test_trusted_proxy_chain_returns_nearest_untrusted_address(self):
        request = self.factory.get(
            "/api/v1/auth/login/",
            REMOTE_ADDR="10.0.0.2",
            HTTP_X_FORWARDED_FOR="203.0.113.9, 10.0.0.1",
        )

        self.assertEqual(get_client_ip(request), "203.0.113.9")

    @override_settings(TRUSTED_PROXY_IPS=("10.0.0.0/8",))
    def test_malformed_forwarded_chain_falls_back_to_proxy_address(self):
        request = self.factory.get(
            "/api/v1/auth/login/",
            REMOTE_ADDR="10.0.0.2",
            HTTP_X_FORWARDED_FOR="not-an-ip",
        )

        self.assertEqual(get_client_ip(request), "10.0.0.2")

    @override_settings(
        TRUST_PROXY_HEADERS=True,
        TRUSTED_PROXY_IPS=("10.0.0.0/8",),
    )
    def test_untrusted_peer_has_all_forwarded_headers_removed(self):
        request = self.factory.get(
            "/api/v1/auth/login/",
            REMOTE_ADDR="198.51.100.8",
            HTTP_X_FORWARDED_FOR="203.0.113.9",
            HTTP_X_FORWARDED_HOST="attacker.example",
            HTTP_X_FORWARDED_PROTO="https",
        )
        middleware = TrustedProxyHeadersMiddleware(lambda req: req)

        processed_request = middleware(request)

        self.assertNotIn("HTTP_X_FORWARDED_FOR", processed_request.META)
        self.assertNotIn("HTTP_X_FORWARDED_HOST", processed_request.META)
        self.assertNotIn("HTTP_X_FORWARDED_PROTO", processed_request.META)

    @override_settings(
        TRUST_PROXY_HEADERS=True,
        TRUSTED_PROXY_IPS=("10.0.0.0/8",),
    )
    def test_trusted_peer_keeps_forwarded_headers(self):
        request = self.factory.get(
            "/api/v1/auth/login/",
            REMOTE_ADDR="10.0.0.2",
            HTTP_X_FORWARDED_FOR="203.0.113.9",
            HTTP_X_FORWARDED_PROTO="https",
        )
        middleware = TrustedProxyHeadersMiddleware(lambda req: req)

        processed_request = middleware(request)

        self.assertEqual(
            processed_request.META["HTTP_X_FORWARDED_FOR"],
            "203.0.113.9",
        )
        self.assertEqual(processed_request.META["HTTP_X_FORWARDED_PROTO"], "https")

    @override_settings(DEBUG=False)
    def test_login_cookies_have_security_attributes(self):
        response = HttpResponse()
        device_id = uuid.uuid4()

        set_login_cookies(
            response,
            refresh_token="refresh-value",
            device_id=device_id,
        )

        refresh_cookie = response.cookies["refresh_token"]
        device_cookie = response.cookies[DEVICE_COOKIE_NAME]
        for cookie in (refresh_cookie, device_cookie):
            self.assertTrue(cookie["secure"])
            self.assertTrue(cookie["httponly"])
            self.assertEqual(cookie["samesite"], "Lax")
            self.assertEqual(cookie["path"], "/api/v1/auth/")

    def test_auth_response_is_not_cacheable(self):
        response = HttpResponse()

        prevent_response_caching(response)

        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("private", response["Cache-Control"])
        self.assertEqual(response["Pragma"], "no-cache")

    def test_clear_login_cookies_uses_their_original_paths(self):
        response = HttpResponse()

        clear_login_cookies(response)

        self.assertEqual(response.cookies["refresh_token"]["path"], "/api/v1/auth/")
        self.assertEqual(
            response.cookies[DEVICE_COOKIE_NAME]["path"],
            "/api/v1/auth/",
        )
        for cookie in response.cookies.values():
            self.assertEqual(cookie["max-age"], 0)

    @override_settings(DEBUG=False)
    def test_refresh_cookie_can_use_remaining_session_lifetime(self):
        response = HttpResponse()

        set_refresh_cookie(
            response,
            refresh_token="rotated-refresh",
            max_age=900,
        )

        cookie = response.cookies["refresh_token"]
        self.assertEqual(cookie["max-age"], 900)
        self.assertTrue(cookie["secure"])
        self.assertTrue(cookie["httponly"])
