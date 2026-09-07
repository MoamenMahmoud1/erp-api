"""Tests for JWT validation followed by Redis-backed session authentication."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import AccessToken

from authsession.cache import cache_active_session, delete_auth_session_cache
from authsession.http import ClientContext
from authsession.services import start_auth_session
from authentication.redis_session import RedisSessionAuthentication


class RedisSessionAuthTests(TestCase):
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
        self.session_result = start_auth_session(
            user=self.user,
            client_context=ClientContext(
                device_id=None,
                device_name="Test device",
                user_agent="Test browser",
                ip_address="127.0.0.1",
            ),
        )
        self.access = AccessToken(self.session_result.access_token)
        self.session = self.user.auth_sessions.get(pk=self.session_result.session_id)
        cache_active_session(
            auth_session=self.session,
            user=self.user,
            access_token=self.access,
        )

    def test_authentication_performs_zero_db_queries_after_jwt_validation(self):
        request = self.factory.get("/api/v1/invoices/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.session_result.access_token}"

        authentication = RedisSessionAuthentication()
        with CaptureQueriesContext(connection) as ctx:
            authenticated = authentication.authenticate(request)

        self.assertIsNotNone(authenticated)
        token_user, _ = authenticated
        self.assertEqual(str(token_user.pk), str(self.user.pk))
        self.assertEqual(ctx.captured_queries, [])

    def test_request_user_is_hydrated_from_redis_snapshot(self):
        request = self.factory.get("/api/v1/invoices/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.session_result.access_token}"

        token_user, _ = RedisSessionAuthentication().authenticate(request)

        self.assertEqual(token_user.username, self.user.username)
        self.assertTrue(token_user.is_staff)
        self.assertEqual(token_user.role_level, 0)
        self.assertTrue(token_user.has_perm("invoices.add_invoice"))

    def test_access_token_has_only_identity_and_session_metadata(self):
        access = AccessToken(self.session_result.access_token)
        self.assertIn("user_id", access.payload)
        self.assertIn("sid", access.payload)
        self.assertNotIn("permissions", access.payload)
        self.assertNotIn("role_level", access.payload)
        self.assertNotIn("is_staff", access.payload)
        self.assertNotIn("is_superuser", access.payload)

    def test_revoking_session_cache_immediately_rejects_access_token(self):
        request = self.factory.get("/api/v1/invoices/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {self.session_result.access_token}"

        delete_auth_session_cache(self.session.id)

        with self.assertRaises(Exception) as error:
            RedisSessionAuthentication().authenticate(request)

        self.assertIn("authentication session", str(error.exception).lower())

    def test_invalid_jwt_is_rejected_without_db_lookup(self):
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
