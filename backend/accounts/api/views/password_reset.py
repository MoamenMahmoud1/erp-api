from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.api.serializers.password_reset import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)
from authsession.http import NoStoreResponseMixin, clear_login_cookies
from authentication.throttling import PasswordResetThrottle


class PasswordResetRequestView(NoStoreResponseMixin, GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (PasswordResetThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetConfirmView(NoStoreResponseMixin, GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (PasswordResetThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_login_cookies(response)
        return response
