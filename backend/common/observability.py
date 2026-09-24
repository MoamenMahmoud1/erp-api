"""Helpers for structured business-operation logging."""
import logging

from core.middleware import get_current_request_id  # noqa: F401

logger = logging.getLogger("erp.operations")


def log_operation(operation, *, user=None, **attrs):
    """Log a business operation and its non-sensitive identifiers."""
    parts = [f"operation={operation}"]
    if user is not None:
        parts.append(f"user={user}")
    for key, value in attrs.items():
        parts.append(f"{key}={value}")
    logger.info(" ".join(parts))
