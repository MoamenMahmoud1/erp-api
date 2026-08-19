"""
Base settings shared between development & production.
"""

from datetime import timedelta
from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config(
    "SECRET_KEY",
    default="dev-only-insecure-secret-key-change-me-0123456789abcdef",
)

FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="no-reply@apihigh.local")
EMAIL_VERIFICATION_TIMEOUT = config(
    "EMAIL_VERIFICATION_TIMEOUT",
    default=60 * 60 * 24,
    cast=int,
)
EMAIL_CHANGE_TIMEOUT = config(
    "EMAIL_CHANGE_TIMEOUT",
    default=60 * 60,
    cast=int,
)


AUTH_USER_MODEL = 'accounts.CustomUserModel'


AUTHENTICATION_BACKENDS = [
    "authentication.email.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    "corsheaders",
    'rest_framework',
    'phonenumber_field',
]

PROJECT_APPS = [
    'accounts.apps.AccountsConfig',
    'authsession.apps.AuthSessionConfig',
    'organization.apps.OrganizationConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS

MIDDLEWARE = [
    "core.middleware.TrustedProxyHeadersMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'common.pagination.DefaultPagination',
    'DEFAULT_THROTTLE_CLASSES': (),
    'DEFAULT_THROTTLE_RATES': {
        'login_burst': '5/min',
        'login_sustained': '30/hour',
        'refresh_burst': '30/min',
        'password_reset': '5/min',
        'signup': '5/hour',
        'email_action': '5/min',
        'sensitive_action': '10/min',
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "SIGNING_KEY": config(
        "JWT_SIGNING_KEY",
        default="dev-only-jwt-signing-key-change-me-0123456789abcdef",
    ),
    "CHECK_REVOKE_TOKEN": True,
}
AUTH_SESSION_MIN_AGE = timedelta(
    hours=config("AUTH_SESSION_MIN_AGE_HOURS", default=168, cast=int)
)
AUTH_SESSION_VERIFICATION_TTL = timedelta(
    minutes=config("AUTH_SESSION_VERIFICATION_MINUTES", default=15, cast=int)
)
CORS_ALLOW_CREDENTIALS = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOG_LEVEL = config('LOG_LEVEL', default='INFO').upper()
DJANGO_LOG_LEVEL = config('DJANGO_LOG_LEVEL', default='WARNING').upper()

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '{asctime} {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': DJANGO_LOG_LEVEL,
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}
