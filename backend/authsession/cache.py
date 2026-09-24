"""Cache active authentication-session state for fast request authentication.

PostgreSQL remains the source of truth for every AuthSession, including revoked
and expired records. Redis stores only the small snapshot needed by hot-path
request authentication and expires with the current access token.
"""

from datetime import datetime, timezone as datetime_timezone

from django.core.cache import cache

from accounts.models import RoleProfile


AUTH_SESSION_CACHE_PREFIX = "authsession"


def auth_session_cache_key(session_id):
    return f"{AUTH_SESSION_CACHE_PREFIX}:{session_id}"


def cache_active_session(*, auth_session, user, access_token):
    """Store the authorization snapshot for exactly the access-token lifetime."""
    expires_at = datetime.fromtimestamp(
        int(access_token["exp"]),
        tz=datetime_timezone.utc,
    )
    timeout = max(
        1,
        int((expires_at - datetime.now(datetime_timezone.utc)).total_seconds()),
    )
    role = RoleProfile.summary_for_user(user)

    cache.set(
        auth_session_cache_key(auth_session.id),
        {
            "session_id": str(auth_session.id),
            "user_id": user.pk,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": bool(user.is_active),
            "is_staff": bool(user.is_staff),
            "is_superuser": bool(user.is_superuser),
            "role_level": role["level"] if role else RoleProfile.level_for_user(user),
            "role_scope": role["scope"] if role else RoleProfile.Scope.SITE,
            "requires_shift": role["requires_shift"] if role else False,
            "role": role,
            "permissions": sorted(user.get_all_permissions()),
            "device_id": str(auth_session.device_id),
            "current_refresh_jti": str(auth_session.current_refresh_jti),
            "verified_at": auth_session.verified_at,
            "access_expires_at": expires_at,
        },
        timeout=timeout,
    )


def delete_auth_session_cache(session_id):
    cache.delete(auth_session_cache_key(session_id))


def delete_auth_session_caches(session_ids):
    cache.delete_many(
        [auth_session_cache_key(session_id) for session_id in session_ids]
    )


def delete_all_auth_session_caches():
    """Invalidate every active authorization snapshot after global RBAC changes."""
    from authsession.models import AuthSession

    session_ids = AuthSession.objects.filter(
        revoked_at__isnull=True,
    ).values_list("pk", flat=True)
    delete_auth_session_caches(session_ids)
