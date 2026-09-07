from django.core.cache import cache
from redis.exceptions import RedisError
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication
from rest_framework_simplejwt.settings import api_settings

from authsession.cache import auth_session_cache_key
from authentication.token_user import ERPTokenUser


class RedisSessionAuthentication(JWTStatelessUserAuthentication):
    """Validate the JWT locally, then load its active session snapshot from Redis."""

    def get_user(self, validated_token):
        session_id = validated_token.get("sid")
        user_id = validated_token.get(api_settings.USER_ID_CLAIM)
        if not session_id or user_id is None:
            raise AuthenticationFailed("Invalid authentication session.")

        try:
            snapshot = cache.get(auth_session_cache_key(session_id))
        except RedisError as error:
            raise AuthenticationFailed("Authentication service unavailable.") from error

        if not snapshot or str(snapshot.get("session_id")) != str(session_id):
            raise AuthenticationFailed("Invalid or expired authentication session.")
        if str(snapshot.get("user_id")) != str(user_id):
            raise AuthenticationFailed("Invalid authentication session.")

        return ERPTokenUser(validated_token, snapshot=snapshot)
