"""Test settings using the same PostgreSQL engine as production."""

from .settings_prod import *  # noqa: F401,F403

DEBUG = False
SECURE_SSL_REDIRECT = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# The Django test client uses HTTP by default. Keep auth cookies usable in
# integration tests without weakening the production cookie policy.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["CONN_HEALTH_CHECKS"] = False
DATABASES["default"]["OPTIONS"] = {}
