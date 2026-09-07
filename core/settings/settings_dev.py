from .settings_base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
AUTH_COOKIE_SECURE = False

# The React/Vite development server runs on port 5173.
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173")
REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/1")

INSTALLED_APPS += [
    'django_extensions',
    #'silk',
]

#MIDDLEWARE.insert(1, 'silk.middleware.SilkyMiddleware')

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
                "min_size": 2,
                "max_size": 20,
                "max_lifetime": 3600,
                "max_idle": 600,
            },
        },
    },
}
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Keep the required local development origins even when the .env file
# provides a custom origin list. This prevents local frontend ports from
# silently replacing the safe development defaults.
def _origins_from_env(name):
    value = config(name, default="")
    return [origin.strip() for origin in value.split(',') if origin.strip()]


DEV_FRONTEND_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://localhost:3000",
]

CORS_ALLOWED_ORIGINS = list(dict.fromkeys([
    *DEV_FRONTEND_ORIGINS,
    *_origins_from_env('CORS_ALLOWED_ORIGINS'),
]))

CSRF_TRUSTED_ORIGINS = list(dict.fromkeys([
    *DEV_FRONTEND_ORIGINS,
    *_origins_from_env('CSRF_TRUSTED_ORIGINS'),
]))

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'TIMEOUT': 300,
    },
}

TRUSTED_PROXY_IPS = ()

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
