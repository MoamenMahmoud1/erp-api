from django.contrib.auth.models import UserManager


class CustomUserManager(UserManager):
    def _create_user(self, username, email, password, **extra_fields):
        if not email or not email.strip():
            raise ValueError("The email field must be set.")
        return super()._create_user(
            username,
            self.normalize_email(email.strip()),
            password,
            **extra_fields,
        )
