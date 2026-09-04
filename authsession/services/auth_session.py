import uuid
from dataclasses import dataclass
from datetime import datetime, timezone as datetime_timezone

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from accounts.models.role import Role
from authsession.http import ClientContext
from authsession.models import AuthSession


@dataclass(frozen=True, slots=True)
class AuthSessionResult:
    session_id: uuid.UUID
    device_id: uuid.UUID
    access_token: str
    refresh_token: str


@dataclass(frozen=True, slots=True)
class RefreshSessionResult:
    access_token: str
    refresh_token: str
    refresh_max_age: int


class InvalidAuthSession(Exception):
    pass


class AuthSessionTooNew(Exception):
    def __init__(self, eligible_at):
        self.eligible_at = eligible_at


def _set_authorization_claims(token, user):
    """Populate only the authorization claims needed by stateless requests."""
    token["is_staff"] = bool(user.is_staff)
    token["is_superuser"] = bool(user.is_superuser)
    token["role_level"] = Role.level_for_user(user)
    token["permissions"] = sorted(user.get_all_permissions())


def _presented_session(refresh_token, access_token):
    try:
        refresh = RefreshToken(refresh_token)
        refresh_session_id = uuid.UUID(refresh["sid"])
        access_session_id = uuid.UUID(access_token["sid"])
        refresh_jti = uuid.UUID(refresh["jti"])
        refresh_user_id = str(refresh[api_settings.USER_ID_CLAIM])
        access_user_id = str(access_token[api_settings.USER_ID_CLAIM])
    except (KeyError, TypeError, ValueError, TokenError) as error:
        raise InvalidAuthSession from error

    if refresh_session_id != access_session_id or refresh_user_id != access_user_id:
        raise InvalidAuthSession

    return refresh, refresh_session_id, refresh_jti, refresh_user_id


def _session_matches(*, auth_session, refresh_jti, user_id, device_id):
    return (
        auth_session.revoked_at is None
        and auth_session.expires_at > timezone.now()
        and auth_session.user_id == user_id
        and auth_session.device_id == device_id
        and auth_session.current_refresh_jti == refresh_jti
    )


def get_current_auth_session(*, user_id, access_token, refresh_token, device_id):
    _refresh, session_id, refresh_jti, token_user_id = _presented_session(
        refresh_token,
        access_token,
    )
    if str(user_id) != token_user_id:
        raise InvalidAuthSession

    try:
        auth_session = AuthSession.objects.get(pk=session_id)
    except AuthSession.DoesNotExist as error:
        raise InvalidAuthSession from error

    if not _session_matches(
        auth_session=auth_session,
        refresh_jti=refresh_jti,
        user_id=user_id,
        device_id=device_id,
    ):
        raise InvalidAuthSession
    return auth_session


def verify_current_auth_session(
    *,
    user,
    access_token,
    refresh_token,
    device_id,
    password,
):
    _refresh, session_id, refresh_jti, token_user_id = _presented_session(
        refresh_token,
        access_token,
    )
    if str(user.pk) != token_user_id:
        raise InvalidAuthSession

    now = timezone.now()
    with transaction.atomic():
        try:
            auth_session = AuthSession.objects.select_for_update().get(pk=session_id)
        except AuthSession.DoesNotExist as error:
            raise InvalidAuthSession from error

        if not _session_matches(
            auth_session=auth_session,
            refresh_jti=refresh_jti,
            user_id=user.pk,
            device_id=device_id,
        ):
            raise InvalidAuthSession

        eligible_at = auth_session.created_at + settings.AUTH_SESSION_MIN_AGE
        if eligible_at > now:
            raise AuthSessionTooNew(eligible_at)
        if not user.check_password(password):
            raise InvalidAuthSession

        auth_session.verified_at = now
        auth_session.save(update_fields=("verified_at",))

    return auth_session


def start_auth_session(*, user, client_context: ClientContext):
    session_id = uuid.uuid4()

    with transaction.atomic():
        locked_user = (
            user.__class__._default_manager.select_for_update().get(pk=user.pk)
        )
        if not locked_user.is_active:
            raise InvalidAuthSession

        refresh = RefreshToken.for_user(locked_user)
        refresh["sid"] = str(session_id)
        _set_authorization_claims(refresh, locked_user)
        access = refresh.access_token
        expires_at = datetime.fromtimestamp(
            refresh["exp"],
            tz=datetime_timezone.utc,
        )

        AuthSession.objects.filter(
            user_id=locked_user.pk,
            device_id=client_context.device_id,
            revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())

        AuthSession.objects.create(
            id=session_id,
            user_id=locked_user.pk,
            device_id=client_context.device_id,
            device_name=client_context.device_name,
            user_agent=client_context.user_agent,
            ip_address=client_context.ip_address,
            current_refresh_jti=uuid.UUID(refresh["jti"]),
            expires_at=expires_at,
        )

    return AuthSessionResult(
        session_id=session_id,
        device_id=client_context.device_id,
        access_token=str(access),
        refresh_token=str(refresh),
    )


def refresh_auth_session(*, refresh_token, client_context: ClientContext):
    try:
        presented_refresh = RefreshToken(refresh_token)
        session_id = uuid.UUID(presented_refresh["sid"])
        presented_jti = uuid.UUID(presented_refresh["jti"])
        token_user_id = str(presented_refresh[api_settings.USER_ID_CLAIM])
    except (KeyError, TypeError, ValueError, TokenError) as error:
        raise InvalidAuthSession from error

    now = timezone.now()
    invalid_session = False

    try:
        with transaction.atomic():
            auth_session = (
                AuthSession.objects.select_for_update()
                .select_related("user")
                .get(id=session_id)
            )

            if auth_session.revoked_at is not None or auth_session.expires_at <= now:
                invalid_session = True
            elif not auth_session.user.is_active:
                auth_session.revoked_at = now
                auth_session.save(update_fields=("revoked_at",))
                invalid_session = True
            elif (
                auth_session.device_id != client_context.device_id
                or auth_session.current_refresh_jti != presented_jti
                or str(auth_session.user_id) != token_user_id
            ):
                auth_session.revoked_at = now
                auth_session.save(update_fields=("revoked_at",))
                invalid_session = True
            else:
                client_changed = (
                    auth_session.user_agent != client_context.user_agent
                    or auth_session.ip_address != client_context.ip_address
                )
                new_refresh = RefreshToken.for_user(auth_session.user)
                new_refresh["sid"] = str(auth_session.id)
                _set_authorization_claims(new_refresh, auth_session.user)
                new_refresh["exp"] = int(auth_session.expires_at.timestamp())

                new_access = new_refresh.access_token
                new_access["exp"] = min(
                    new_access["exp"],
                    new_refresh["exp"],
                )

                auth_session.current_refresh_jti = uuid.UUID(new_refresh["jti"])
                auth_session.last_refreshed_at = now
                auth_session.user_agent = client_context.user_agent
                auth_session.ip_address = client_context.ip_address
                if client_changed:
                    auth_session.verified_at = None
                auth_session.save(
                    update_fields=(
                        "current_refresh_jti",
                        "last_refreshed_at",
                        "user_agent",
                        "ip_address",
                        "verified_at",
                    )
                )
    except AuthSession.DoesNotExist as error:
        raise InvalidAuthSession from error

    if invalid_session:
        raise InvalidAuthSession

    return RefreshSessionResult(
        access_token=str(new_access),
        refresh_token=str(new_refresh),
        refresh_max_age=max(
            0,
            int((auth_session.expires_at - now).total_seconds()),
        ),
    )


def revoke_auth_session(*, user_id, refresh_token, device_id):
    try:
        refresh = RefreshToken(refresh_token)
        session_id = uuid.UUID(refresh["sid"])
        token_user_id = str(refresh[api_settings.USER_ID_CLAIM])
    except (KeyError, TypeError, ValueError, TokenError):
        return

    if str(user_id) != token_user_id:
        return

    AuthSession.objects.filter(
        id=session_id,
        user_id=user_id,
        device_id=device_id,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())


def revoke_all_sessions(*, user_id):
    return AuthSession.objects.filter(
        user_id=user_id,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())
