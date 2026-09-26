from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from authsession.models import AuthSession


def purge_auth_sessions(*, revoked_retention_days=30):
    if revoked_retention_days < 0:
        raise ValueError("Retention days cannot be negative.")

    now = timezone.now()
    revoked_cutoff = now - timedelta(days=revoked_retention_days)
    queryset = AuthSession.objects.filter(
        Q(expires_at__lte=now)
        | Q(
            revoked_at__isnull=False,
            revoked_at__lte=revoked_cutoff,
        )
    )
    deleted_count, _ = queryset.delete()
    return deleted_count
