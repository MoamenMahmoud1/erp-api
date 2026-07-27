from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import PermissionDenied


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get("email")

        if not isinstance(email, str) or password is None:
            return None

        email = email.strip()
        if "@" not in email:
            return None

        UserModel = get_user_model()

        try:
            user = UserModel._default_manager.get(email__iexact=email)
        except (UserModel.DoesNotExist, UserModel.MultipleObjectsReturned):
            UserModel().set_password(password)
            raise PermissionDenied

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        raise PermissionDenied
