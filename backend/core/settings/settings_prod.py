from django.core.exceptions import ImproperlyConfigured

from .settings_base import *

DEBUG = False

SECRET_KEY = config("SECRET_KEY")
JWT_SIGNING_KEY = config("JWT_SIGNING_KEY")

if len(SECRET_KEY) < 32:
    raise ImproperlyConfigured("SECRET_KEY must contain at least 32 characters.")
if len(JWT_SIGNING_KEY) < 32:
    raise ImproperlyConfigured("JWT_SIGNING_KEY must contain at least 32 characters.")

SIMPLE_JWT["SIGNING_KEY"] = JWT_SIGNING_KEY

ALLOWED_HOSTS = [
    host.strip()
    for host in config("ALLOWED_HOSTS").split(",")
    if host.strip()
]
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must contain explicit hostnames in production."
    )
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in config("CORS_ALLOWED_ORIGINS").split(",")
    if origin.strip()
]
if not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured(
        "CORS_ALLOWED_ORIGINS must contain at least one origin in production."
    )
ENABLE_API_DOCS = config("ENABLE_API_DOCS", default=False, cast=bool)
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in config("CSRF_TRUSTED_ORIGINS").split(",")
    if origin.strip()
]
if not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured(
        "CSRF_TRUSTED_ORIGINS must contain at least one origin in production."
    )

# PostgreSQL Production
DB_POOL_MIN_SIZE = config("DB_POOL_MIN_SIZE", default=1, cast=int)
DB_POOL_MAX_SIZE = config("DB_POOL_MAX_SIZE", default=5, cast=int)
if DB_POOL_MIN_SIZE < 0 or DB_POOL_MAX_SIZE < 1 or DB_POOL_MIN_SIZE > DB_POOL_MAX_SIZE:
    raise ValueError("DB_POOL_MIN_SIZE and DB_POOL_MAX_SIZE are invalid")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "pool": {
                "min_size": DB_POOL_MIN_SIZE,
                "max_size": DB_POOL_MAX_SIZE,
                "max_lifetime": config("DB_POOL_MAX_LIFETIME", default=3600, cast=int),
                "max_idle": config("DB_POOL_MAX_IDLE", default=600, cast=int),
            },
        },
    },
}

# Static & Media (S3)
INSTALLED_APPS += ["storages"]
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Secure Cookies
AUTH_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "lax"
CSRF_COOKIE_SAMESITE = "lax"

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
TRUST_PROXY_HEADERS = config("TRUST_PROXY_HEADERS", default=False, cast=bool)
USE_X_FORWARDED_HOST = TRUST_PROXY_HEADERS
if TRUST_PROXY_HEADERS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
TRUSTED_PROXY_IPS = config(
    "TRUSTED_PROXY_IPS",
    default="",
    cast=lambda value: tuple(
        item.strip() for item in value.split(",") if item.strip()
    ),
)

# Email SMTP from ENV
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_TIMEOUT = config("EMAIL_TIMEOUT", default=10, cast=int)

# AWS defaults
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="eu-central-1")
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = config("AWS_QUERYSTRING_AUTH", default=True, cast=bool)

# Redis is a cache layer, not the source of truth for AuthSession history.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("REDIS_URL"),
        "TIMEOUT": 300,
    },
}
