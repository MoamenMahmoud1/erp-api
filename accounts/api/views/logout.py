from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authsession.http import (
    NoStoreResponseMixin,
    clear_login_cookies,
    get_device_id,
)
from authsession.services.auth_session import revoke_all_sessions, revoke_auth_session
from authsession.permissions import VerifiedAuthSessionPermission


class LogoutView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        device_id = get_device_id(request)

        if refresh_token and device_id is not None:
            revoke_auth_session(
                user=request.user,
                refresh_token=refresh_token,
                device_id=device_id,
            )

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_login_cookies(response)
        return response


class LogoutAllView(NoStoreResponseMixin, APIView):
    permission_classes = (IsAuthenticated, VerifiedAuthSessionPermission)

    def post(self, request, *args, **kwargs):
        revoke_all_sessions(request.user)

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_login_cookies(response)
        return response
