from django.conf import settings
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authsession.api.serializers import (
    AuthSessionSerializer,
    AuthSessionVerificationSerializer,
)
from authsession.http import NoStoreResponseMixin, clear_login_cookies, get_device_id
from authsession.models import AuthSession
from authsession.permissions import CurrentAuthSessionPermission
from authsession.services import (
    AuthSessionTooNew,
    InvalidAuthSession,
    verify_current_auth_session,
)
from authentication.throttling import SensitiveActionThrottle


class AuthSessionVerificationView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (SensitiveActionThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = AuthSessionVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh_token = request.COOKIES.get("refresh_token")
        device_id = get_device_id(request)
        user = self._resolve_user(request)

        try:
            if not refresh_token or device_id is None:
                raise InvalidAuthSession
            auth_session = verify_current_auth_session(
                user=user,
                access_token=request.auth,
                refresh_token=refresh_token,
                device_id=device_id,
                password=serializer.validated_data["current_password"],
            )
        except AuthSessionTooNew as error:
            return Response(
                {
                    "detail": "This session is not old enough.",
                    "code": "session_too_new",
                    "eligible_at": error.eligible_at,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except InvalidAuthSession:
            return Response(
                {
                    "detail": "Invalid authentication session or password.",
                    "code": "invalid_session_verification",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {
                "verified_until": (
                    auth_session.verified_at
                    + settings.AUTH_SESSION_VERIFICATION_TTL
                )
            },
            status=status.HTTP_200_OK,
        )

    def _resolve_user(self, request):
        """Return the database User needed for stateful session verification."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user_pk = request.user.pk
        if user_pk is None:
            raise AuthenticationFailed("Invalid authentication session.")
        try:
            return User.objects.get(pk=user_pk)
        except User.DoesNotExist as error:
            raise AuthenticationFailed(
                "Invalid authentication session."
            ) from error


class AuthSessionViewSet(
    NoStoreResponseMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AuthSessionSerializer
    permission_classes = (IsAuthenticated, CurrentAuthSessionPermission)

    def get_queryset(self):
        return AuthSession.objects.filter(
            user_id=self.request.user.pk,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).order_by("-last_refreshed_at")

    def destroy(self, request, *args, **kwargs):
        auth_session = self.get_object()
        is_current = get_device_id(request) == auth_session.device_id
        AuthSession.objects.filter(
            pk=auth_session.pk,
            revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())

        response = Response(status=status.HTTP_204_NO_CONTENT)
        if is_current:
            clear_login_cookies(response)
        return response
