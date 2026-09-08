"""Test settings using the same PostgreSQL engine as production."""

from .settings_prod import *  # noqa: F401,F403

DEBUG = False
SECURE_SSL_REDIRECT = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Django's test client uses HTTP. Keep test cookies usable without changing
# the secure-cookie policy used in production.
AUTH_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["CONN_HEALTH_CHECKS"] = False
DATABASES["default"]["OPTIONS"] = {}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "erp-api-test-auth",
    },
}

# Read-only reports must never leak cached results between isolated Django
# TestCase databases. Production keeps the short Redis TTL.
REPORT_CACHE_TTL = 0
