"""Background jobs for management reports."""

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounting.services.analytics import dashboard_overview


@shared_task(
    name="accounting.tasks.warm_analytics_reports",
    ignore_result=True,
)
def warm_analytics_reports(*, as_of=None, lookback_days=30):
    """Populate the common dashboard report cache without blocking HTTP requests."""
    if as_of is None:
        as_of = timezone.localdate()
    start = as_of - timedelta(days=lookback_days - 1)

    dashboard_overview(date_from=start, date_to=as_of)
