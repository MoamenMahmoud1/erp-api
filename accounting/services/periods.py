"""Accounting period controls.

A period is only a date-range lock. Closing it prevents new journal entries
from being created or posted inside that range; it does not create a separate
closing engine.
"""

from django.db import transaction
from django.utils import timezone

from accounting.models import AccountingPeriod, JournalEntry
from common.exceptions import InvalidBusinessOperation


class AccountingPeriodError(InvalidBusinessOperation):
    """Raised when an accounting period operation violates a business rule."""


def assert_period_open(*, entry_date, company):
    """Reject accounting work dated inside a closed period."""
    if AccountingPeriod.objects.filter(
        company=company,
        is_closed=True,
        start_date__lte=entry_date,
        end_date__gte=entry_date,
    ).exists():
        raise AccountingPeriodError(
            f"Accounting period is closed for {entry_date.isoformat()}."
        )


def create_period(*, name, start_date, end_date, company):
    """Create a non-overlapping accounting period."""
    if start_date > end_date:
        raise AccountingPeriodError("Period start date must be on or before its end date.")

    overlapping = AccountingPeriod.objects.filter(
        company=company,
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exists()
    if overlapping:
        raise AccountingPeriodError("Accounting periods cannot overlap.")

    return AccountingPeriod.objects.create(
        company=company,
        name=name,
        start_date=start_date,
        end_date=end_date,
    )


@transaction.atomic
def close_period(*, period_id, actor_id, company):
    """Close a period after ensuring no draft journals remain inside it."""
    period = AccountingPeriod.objects.select_for_update().get(
        pk=period_id,
        company=company,
    )
    if period.is_closed:
        return period

    has_drafts = JournalEntry.objects.filter(
        company=company,
        status=JournalEntry.Status.DRAFT,
        entry_date__gte=period.start_date,
        entry_date__lte=period.end_date,
    ).exists()
    if has_drafts:
        raise AccountingPeriodError(
            "The period cannot be closed while draft journal entries exist inside it."
        )

    period.is_closed = True
    period.closed_by_id = actor_id
    period.closed_at = timezone.now()
    period.save(update_fields=("is_closed", "closed_by", "closed_at", "updated_at"))
    return period
