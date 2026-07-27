from .settings_base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS += [
    'django_extensions',
    'silk',
]

MIDDLEWARE.insert(1, 'silk.middleware.SilkyMiddleware')


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / "db.sqlite3",
    }
}
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_EXPIRE_AT_BROWSER_CLOSE = False


EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'



CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://127.0.0.1:5500,http://localhost:5500,http://localhost:3000',
    cast=lambda value: [origin.strip() for origin in value.split(',') if origin.strip()],
)
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://127.0.0.1:5500,http://localhost:5500,http://localhost:3000',
    cast=lambda value: [origin.strip() for origin in value.split(',') if origin.strip()],
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'apihigh-erp-dev',
    },
}

TRUSTED_PROXY_IPS = ()


SESSION_ENGINE = 'django.contrib.sessions.backends.db'
