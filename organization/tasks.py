"""Scheduled integrity checks for transactional ERP counters."""

from celery import shared_task

from organization.services.metrics import reconcile_company_counters


@shared_task(
    name="organization.tasks.reconcile_company_counters",
    ignore_result=True,
)
def reconcile_company_counters_task():
    """Reconcile denormalized master-data counters with their source tables."""
    return reconcile_company_counters()
