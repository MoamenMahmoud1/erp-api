from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.api.serializers.account_email import (
    EmailChangeConfirmSerializer,
    EmailChangeRequestSerializer,
    EmailVerificationResendSerializer,
    EmailVerificationSerializer,
    SignUpSerializer,
)
from authsession.http import NoStoreResponseMixin, clear_login_cookies
from authsession.permissions import VerifiedAuthSessionPermission
from authentication.throttling import (
    EmailActionThrottle,
    SignUpThrottle,
)


class SignUpView(NoStoreResponseMixin, GenericAPIView):
    serializer_class = SignUpSerializer
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (SignUpThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"id": user.pk, "username": user.username, "email": user.email},
            status=status.HTTP_201_CREATED,
        )


class EmailVerificationView(NoStoreResponseMixin, GenericAPIView):
    serializer_class = EmailVerificationSerializer
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (EmailActionThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmailVerificationResendView(NoStoreResponseMixin, GenericAPIView):
    serializer_class = EmailVerificationResendSerializer
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (EmailActionThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmailChangeRequestView(NoStoreResponseMixin, GenericAPIView):
    serializer_class = EmailChangeRequestSerializer
    permission_classes = (IsAuthenticated, VerifiedAuthSessionPermission)
    throttle_classes = (EmailActionThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmailChangeConfirmView(NoStoreResponseMixin, GenericAPIView):
    serializer_class = EmailChangeConfirmSerializer
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (EmailActionThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_login_cookies(response)
        return response
