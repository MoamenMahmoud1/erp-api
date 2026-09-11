"""
Base settings shared between development & production.
"""

from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="dev-only-insecure-secret-key-change-me-0123456789abcdef")
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="no-reply@apihigh.local")
EMAIL_VERIFICATION_TIMEOUT = config("EMAIL_VERIFICATION_TIMEOUT", default=60 * 60 * 24, cast=int)
EMAIL_CHANGE_TIMEOUT = config("EMAIL_CHANGE_TIMEOUT", default=60 * 60, cast=int)
REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/1")
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)

AUTH_USER_MODEL = "accounts.CustomUserModel"
AUTHENTICATION_BACKENDS = [
    "authentication.email.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "phonenumber_field",
    "django_filters",
]
PROJECT_APPS = [
    "auditlog.apps.AuditlogConfig",
    "accounts.apps.AccountsConfig",
    "authsession.apps.AuthSessionConfig",
    "organization.apps.OrganizationConfig",
    "customers.apps.CustomersConfig",
    "products.apps.ProductsConfig",
    "coupons.apps.CouponsConfig",
    "invoices.apps.InvoicesConfig",
    "payments.apps.PaymentsConfig",
    "inventory.apps.InventoryConfig",
    "purchases.apps.PurchasesConfig",
    "suppliers.apps.SuppliersConfig",
    "accounting.apps.AccountingConfig",
    "notifications.apps.NotificationsConfig",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS
MIDDLEWARE = [
    "core.middleware.RequestCorrelationMiddleware",
    "core.middleware.TrustedProxyHeadersMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("authentication.redis_session.RedisSessionAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exception_handler.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "200/min",
        "login_burst": "5/min",
        "login_sustained": "30/hour",
        "refresh_burst": "30/min",
        "password_reset": "5/min",
        "signup": "5/hour",
        "email_action": "5/min",
        "sensitive_action": "10/min",
    },
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "SIGNING_KEY": config("JWT_SIGNING_KEY", default="dev-only-jwt-signing-key-change-me-0123456789abcdef"),
    "CHECK_REVOKE_TOKEN": False,
    "TOKEN_USER_CLASS": "authentication.token_user.ERPTokenUser",
}
IDEMPOTENCY_RETENTION_DAYS = config("IDEMPOTENCY_RETENTION_DAYS", default=365, cast=int)
if IDEMPOTENCY_RETENTION_DAYS < 1:
    raise ValueError("IDEMPOTENCY_RETENTION_DAYS must be >= 1")
AUTH_SESSION_MIN_AGE = timedelta(hours=config("AUTH_SESSION_MIN_AGE_HOURS", default=168, cast=int))
AUTH_SESSION_VERIFICATION_TTL = timedelta(minutes=config("AUTH_SESSION_VERIFICATION_MINUTES", default=15, cast=int))
CORS_ALLOW_CREDENTIALS = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOG_LEVEL = config("LOG_LEVEL", default="INFO").upper()
DJANGO_LOG_LEVEL = config("DJANGO_LOG_LEVEL", default="WARNING").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"standard": {"format": "{asctime} {levelname} {name} [{request_id}]: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": DJANGO_LOG_LEVEL, "propagate": False},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "accounts": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "erp.operations": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "erp.metrics": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}
INTERNAL_IPS = ["127.0.0.1"]
REPORT_CACHE_TTL = config("REPORT_CACHE_TTL", default=30, cast=int)
if REPORT_CACHE_TTL < 1:
    raise ValueError("REPORT_CACHE_TTL must be >= 1")

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = config("CELERY_TASK_TIME_LIMIT", default=300, cast=int)
CELERY_TASK_SOFT_TIME_LIMIT = config("CELERY_TASK_SOFT_TIME_LIMIT", default=240, cast=int)

CELERY_BEAT_SCHEDULE = {
    "reconcile-company-counters": {
        "task": "organization.tasks.reconcile_company_counters",
        "schedule": crontab(hour=2, minute=0),
    },
    "rebuild-recent-approval-notifications": {
        "task": "notifications.tasks.rebuild_recent_approval_notifications",
        "schedule": crontab(minute="*/1"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Sales ERP API",
    "DESCRIPTION": "Backend API for the Sales ERP suite. Authentication uses short-lived JWT access tokens backed by an active server-side Redis session; include the access token in the Authorization header as `Bearer <token>`. ",
    "VERSION": __import__("core.version", fromlist=["API_VERSION"]).API_VERSION,
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}
