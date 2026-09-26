import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.utils import timezone

from authsession.cache import auth_session_cache_key
from authsession.models import AuthSession


class AuthSessionAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="StrongAdminPassword123!",
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="StrongOtherPassword123!",
        )
        self.model_admin = admin.site._registry[AuthSession]
        self.request = RequestFactory().get("/admin/")
        self.request.user = self.user

    def create_session(self, user=None, revoked_at=None):
        return AuthSession.objects.create(
            user=user or self.other_user,
            device_id=uuid.uuid4(),
            current_refresh_jti=uuid.uuid4(),
            expires_at=timezone.now() + timedelta(days=30),
            revoked_at=revoked_at,
        )

    def test_admin_can_filter_sessions_by_status_and_date(self):
        self.assertEqual(self.model_admin.list_filter[0].__name__, "RevokedFilter")
        self.assertNotIn(
            ("user", admin.RelatedOnlyFieldListFilter),
            self.model_admin.list_filter,
        )
        self.assertEqual(self.model_admin.date_hierarchy, "created_at")
        self.assertEqual(self.model_admin.list_filter[0].parameter_name, "revoked")
        self.assertIn("user__username", self.model_admin.search_fields)
        self.assertIn("user__email", self.model_admin.search_fields)

        active = self.create_session()
        revoked = self.create_session(revoked_at=timezone.now())

        request = RequestFactory().get("/admin/authsession/authsession/")
        filter_class = self.model_admin.list_filter[0]
        instance = filter_class(request, {"revoked": "no"}, AuthSession, self.model_admin)
        no_revoked_ids = set(
            instance.queryset(request, AuthSession.objects.all()).values_list("pk", flat=True)
        )
        self.assertIn(active.pk, no_revoked_ids)
        self.assertNotIn(revoked.pk, no_revoked_ids)

        instance = filter_class(request, {"revoked": "yes"}, AuthSession, self.model_admin)
        revoked_ids = set(
            instance.queryset(request, AuthSession.objects.all()).values_list("pk", flat=True)
        )
        self.assertIn(revoked.pk, revoked_ids)
        self.assertNotIn(active.pk, revoked_ids)

    def test_admin_can_revoke_selected_sessions_and_clear_cache(self):
        session = self.create_session()
        cache.set(
            auth_session_cache_key(session.pk),
            {"session_id": str(session.pk)},
            300,
        )
        queryset = AuthSession.objects.filter(pk=session.pk)

        with (
            self.captureOnCommitCallbacks(execute=True),
            patch.object(self.model_admin, "message_user") as message_user,
        ):
            self.model_admin.revoke_sessions(self.request, queryset)

        session.refresh_from_db()
        self.assertIsNotNone(session.revoked_at)
        self.assertIsNone(cache.get(auth_session_cache_key(session.pk)))
        message_user.assert_called_once()

    def test_admin_does_not_revoke_already_revoked_sessions_again(self):
        revoked_at = timezone.now() - timedelta(hours=1)
        session = self.create_session(revoked_at=revoked_at)

        with patch.object(self.model_admin, "message_user") as message_user:
            self.model_admin.revoke_sessions(
                self.request,
                AuthSession.objects.filter(pk=session.pk),
            )

        session.refresh_from_db()
        self.assertEqual(session.revoked_at, revoked_at)
        message_user.assert_called_once()
