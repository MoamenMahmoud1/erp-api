import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from authsession.http import ClientContext
from authsession.models import AuthSession
from authsession.services.auth_session import (
    AuthSessionResult,
    InvalidAuthSession,
    RefreshSessionResult,
    refresh_auth_session,
    start_auth_session,
)
from common.exceptions import ActiveAuthSession


class AuthSessionConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="concurrency-user",
            email="concurrency@example.com",
            password="StrongPass123!",
        )
        self.context = ClientContext(
            device_id=uuid.uuid4(),
            device_name="Test Device",
            user_agent="Concurrency Test",
            ip_address="192.0.2.50",
        )

    def _run_concurrently(self, operation, workers=2):
        barrier = Barrier(workers)

        def runner():
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return operation()
            except Exception as exc:
                return exc
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=workers) as executor:
            return list(executor.map(lambda _: runner(), range(workers)))

    def test_concurrent_same_device_login_leaves_one_active_session(self):
        if connection.vendor != "postgresql":
            self.skipTest("This test verifies PostgreSQL row-lock semantics.")

        results = self._run_concurrently(
            lambda: start_auth_session(
                user=self.user,
                client_context=self.context,
            ),
        )

        successes = [result for result in results if isinstance(result, AuthSessionResult)]
        conflicts = [result for result in results if isinstance(result, ActiveAuthSession)]

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(
            AuthSession.objects.filter(
                user=self.user,
                device_id=self.context.device_id,
                revoked_at__isnull=True,
            ).count(),
            1,
        )

    def test_concurrent_refresh_reuse_allows_one_rotation_and_revokes_reuse(self):
        if connection.vendor != "postgresql":
            self.skipTest("This test verifies PostgreSQL row-lock semantics.")

        login = start_auth_session(
            user=self.user,
            client_context=self.context,
        )
        old_refresh = RefreshToken(login.refresh_token)

        results = self._run_concurrently(
            lambda: refresh_auth_session(
                refresh_token=login.refresh_token,
                client_context=self.context,
            ),
        )

        successes = [result for result in results if isinstance(result, RefreshSessionResult)]
        failures = [result for result in results if isinstance(result, InvalidAuthSession)]

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)

        session = AuthSession.objects.get(pk=login.session_id)
        self.assertIsNotNone(session.revoked_at)
        self.assertNotEqual(
            RefreshToken(successes[0].refresh_token)["jti"],
            old_refresh["jti"],
        )
