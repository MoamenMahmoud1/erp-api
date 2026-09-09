"""Small Redis-backed cache helper for read-only management reports."""

import hashlib
import json
from functools import wraps

from django.conf import settings
from django.core.cache import cache

REPORT_CACHE_VERSION_KEY = "erp:report:version"


def _cache_version():
    return cache.get(REPORT_CACHE_VERSION_KEY, 1)


def invalidate_report_cache():
    """Invalidate every cached report without scanning or deleting Redis keys."""
    try:
        cache.incr(REPORT_CACHE_VERSION_KEY)
    except ValueError:
        cache.set(REPORT_CACHE_VERSION_KEY, 2, timeout=None)


def cached_report(name, timeout=None):
    """Cache deterministic report calls for a short configurable TTL.

    The namespace version makes invalidation cheap and backend-agnostic. Old
    entries expire naturally; new reads use the current version immediately.
    """
    ttl = timeout if timeout is not None else getattr(settings, "REPORT_CACHE_TTL", 30)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            payload = json.dumps(
                {"args": args, "kwargs": kwargs},
                default=str,
                sort_keys=True,
                separators=(",", ":"),
            )
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
            version = _cache_version()
            key = f"erp:report:v{version}:{name}:{digest}"
            cached = cache.get(key)
            if cached is not None:
                return cached
            value = func(*args, **kwargs)
            cache.set(key, value, ttl)
            return value

        return wrapper

    return decorator
