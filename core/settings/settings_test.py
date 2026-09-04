"""Test settings using the same PostgreSQL engine as production."""

from .settings_prod import *  # noqa: F401,F403

DEBUG = False
SECURE_SSL_REDIRECT = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["CONN_HEALTH_CHECKS"] = False
DATABASES["default"]["OPTIONS"] = {}
