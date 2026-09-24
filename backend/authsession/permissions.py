from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import BasePermission

from authsession.http import get_device_id
from authsession.services import InvalidAuthSession, get_current_auth_session


class CurrentAuthSessionPermission(BasePermission):
    """Verify the stateful auth session using the JWT identity claim."""

    def has_permission(self, request, view):
        refresh_token = request.COOKIES.get("refresh_token")
        device_id = get_device_id(request)
        user_id = request.user.pk
        if not refresh_token or device_id is None or user_id is None:
            raise AuthenticationFailed("Invalid authentication session.")

        try:
            auth_session = get_current_auth_session(
                user_id=user_id,
                access_token=request.auth,
                refresh_token=refresh_token,
                device_id=device_id,
            )
        except InvalidAuthSession as error:
            raise AuthenticationFailed(
                "Invalid authentication session."
            ) from error

        request.auth_session = auth_session
        return True


class VerifiedAuthSessionPermission(CurrentAuthSessionPermission):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        auth_session = request.auth_session

        if (
            auth_session.verified_at is None
            or auth_session.verified_at
            < timezone.now() - settings.AUTH_SESSION_VERIFICATION_TTL
        ):
            raise PermissionDenied(
                "Recent session verification is required.",
                code="session_verification_required",
            )

        return True
