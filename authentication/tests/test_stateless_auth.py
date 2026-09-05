"""Tests proving that JWT access-token authentication is stateless."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from authsession.services.auth_session import _set_authorization_claims


class StatelessAuthTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="stateless-user",
            email="stateless@example.com",
            password="StrongPass123!",
            is_active=True,
            is_verified=True,
            is_staff=True,
        )
        self.permission = Permission.objects.get(
            content_type__app_label="invoices",
            codename="add_invoice",
        )
        self.user.user_permissions.add(self.permission)
        self.factory = APIRequestFactory()

    def _make_access_token(self):
        refresh = RefreshToken.for_user(self.user)
        _set_authorization_claims(refresh, self.user)
        return str(refresh.access_token)

    def test_real_jwt_authentication_performs_zero_db_queries(self):
        request = self.factory.get("/api/v1/invoices/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self._make_access_token()}"

        authentication = JWTStatelessUserAuthentication()
        with CaptureQueriesContext(connection) as ctx:
            authenticated = authentication.authenticate(request)

        self.assertIsNotNone(authenticated)
        token_user, _ = authenticated
        self.assertEqual(str(token_user.pk), str(self.user.pk))
        self.assertEqual(ctx.captured_queries, [])

    def test_stateless_user_preserves_authorization_claims(self):
        request = self.factory.get("/api/v1/invoices/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self._make_access_token()}"

        token_user, _ = JWTStatelessUserAuthentication().authenticate(request)

        self.assertTrue(token_user.is_staff)
        self.assertTrue(token_user.has_perm("invoices.add_invoice"))

    def test_access_token_contains_no_password_derived_claim(self):
        access = AccessToken(self._make_access_token())
        self.assertNotIn("hash_password", access.payload)

    def test_invalid_token_is_rejected_without_db_lookup(self):
        request = self.factory.get("/api/v1/invoices/")
        request.META["HTTP_AUTHORIZATION"] = "Bearer invalid.token.value"

        authentication = JWTStatelessUserAuthentication()
        with CaptureQueriesContext(connection) as ctx:
            with self.assertRaises(InvalidToken):
                authentication.authenticate(request)

        self.assertEqual(ctx.captured_queries, [])


class NoRevokeTokenCheckTests(TestCase):
    def test_check_revoke_token_is_disabled(self):
        from django.conf import settings

        self.assertFalse(settings.SIMPLE_JWT.get("CHECK_REVOKE_TOKEN", False))
