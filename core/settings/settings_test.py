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

# Task tests must remain deterministic and never require a local broker.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"

# The project intentionally does not commit generated migration files for every app.
# CI/test databases are built from the current model state instead.
PROJECT_APP_LABELS = [
    "accounts",
    "authsession",
    "organization",
    "customers",
    "customer_assignments",
    "products",
    "coupons",
    "invoices",
    "payments",
    "inventory",
    "purchases",
    "suppliers",
    "accounting",
    "auditlog",
    "notifications",
]
MIGRATIONLESS_TEST_APPS = PROJECT_APP_LABELS + [
    "admin",
    "auth",
    "contenttypes",
    "sessions",
]
MIGRATION_MODULES = {label: None for label in MIGRATIONLESS_TEST_APPS}
