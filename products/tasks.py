"""Background jobs for product intelligence."""

from celery import shared_task
from django.utils import timezone

from products.services.intelligence import product_intelligence


@shared_task(
    name="products.tasks.refresh_product_intelligence",
    ignore_result=True,
)
def refresh_product_intelligence(*, as_of=None):
    """Refresh the default product intelligence snapshot in the report cache."""
    if as_of is None:
        as_of = timezone.localdate()
    product_intelligence(as_of=as_of)
