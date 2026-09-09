"""Coordinate report invalidation with successful domain transactions."""

import logging

from django.core.cache import cache
from django.db import transaction

from common.report_cache import invalidate_report_cache

logger = logging.getLogger(__name__)


def schedule_report_refresh(*, refresh_product_intelligence=False):
    """Invalidate report cache and enqueue background warming after commit.

    Report invalidation is coupled to the transaction boundary, while Celery
    failure is intentionally non-fatal: transactional ERP writes must not fail
    because the analytics worker or broker is temporarily unavailable.
    """

    def _after_commit():
        invalidate_report_cache()
        try:
            from accounting.tasks import warm_analytics_reports

            warm_analytics_reports.delay()
            if refresh_product_intelligence:
                from products.tasks import refresh_product_intelligence as refresh_task

                refresh_task.delay()
        except Exception:
            logger.exception("Unable to enqueue post-commit report refresh")

    transaction.on_commit(_after_commit)


def clear_report_refresh_state():
    """Testing helper for the optional report-refresh coordination state."""
    cache.delete("erp:report:refresh:queued")
