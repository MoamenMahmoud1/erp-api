"""Small Redis-backed cache helper for read-only management reports."""

import hashlib
import json
from functools import wraps

from django.conf import settings
from django.core.cache import cache


def cached_report(name, timeout=None):
    """Cache deterministic report calls for a short configurable TTL."""
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
            key = f"erp:report:{name}:{digest}"
            cached = cache.get(key)
            if cached is not None:
                return cached
            value = func(*args, **kwargs)
            cache.set(key, value, ttl)
            return value

        return wrapper

    return decorator
