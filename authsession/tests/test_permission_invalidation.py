import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from authsession.cache import auth_session_cache_key
from authsession.models import AuthSession


class PermissionInvalidationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="permission-invalidation-user",
            email="permission-invalidation@example.com",
            password="StrongPass123!",
        )
        self.permission = Permission.objects.get(
            content_type__app_label="products",
            codename="view_product",
        )

    def _session(self, user=None):
        user = user or self.user
        session_id = uuid.uuid4()
        expires_at = timezone.now() + timedelta(hours=1)
        AuthSession.objects.create(
            id=session_id,
            user=user,
            current_refresh_jti=uuid.uuid4(),
            expires_at=expires_at,
        )
        cache.set(auth_session_cache_key(session_id), {"user_id": user.pk}, 300)
        return session_id

    def test_direct_permission_change_invalidates_active_session_cache(self):
        session_id = self._session()
        self.assertIsNotNone(cache.get(auth_session_cache_key(session_id)))

        self.user.user_permissions.add(self.permission)

        self.assertIsNone(cache.get(auth_session_cache_key(session_id)))

    def test_group_permission_change_invalidates_member_session_cache(self):
        from django.contrib.auth.models import Group

        group = Group.objects.create(name="Inventory Readers")
        group.user_set.add(self.user)
        session_id = self._session()
        self.assertIsNotNone(cache.get(auth_session_cache_key(session_id)))

        group.permissions.add(self.permission)

        self.assertIsNone(cache.get(auth_session_cache_key(session_id)))
