"""
Observability helpers for business-operation logging.

Every critical business operation logs a structured line that includes the
request correlation id (when available), the acting user, the operation name,
and contextual attributes.  This does NOT log sensitive financial values,
passwords, tokens, or PII beyond what is needed to identify the object.

The logger is configured in Django's LOGGING setting — no manual handler
setup here.  The ``request_id`` attribute is injected by the
``_RequestIdLogRecordFactory`` installed in ``core.middleware``.
"""
import logging

from core.middleware import get_current_request_id  # noqa: F401

logger = logging.getLogger("erp.operations")


def log_operation(operation, *, user=None, **attrs):
    """Log a business operation at INFO level.

    ``operation`` is a stable dotted name such as ``invoice.confirm``.
    ``attrs`` are extra context fields (object ids, outcomes, etc.).
    Sensitive fields (cash amounts, tokens, passwords) must NOT be passed.
    """
    parts = [f"operation={operation}"]
    if user is not None:
        parts.append(f"user={user}")
    for key, value in attrs.items():
        parts.append(f"{key}={value}")
    logger.info(" ".join(parts))
