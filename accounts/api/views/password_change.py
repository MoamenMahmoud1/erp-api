from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.api.serializers.password_change import PasswordChangeSerializer
from authsession.http import NoStoreResponseMixin, clear_login_cookies
from authsession.permissions import VerifiedAuthSessionPermission
from authentication.throttling import SensitiveActionThrottle


class PasswordChangeView(NoStoreResponseMixin, GenericAPIView):
    serializer_class = PasswordChangeSerializer
    permission_classes = (IsAuthenticated, VerifiedAuthSessionPermission)
    throttle_classes = (SensitiveActionThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_login_cookies(response)
        return response
