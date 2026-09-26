from celery import shared_task
from django.conf import settings

from authsession.services.cleanup import purge_auth_sessions as run_purge_auth_sessions


@shared_task(
    name="authsession.tasks.purge_auth_sessions",
    ignore_result=True,
)
def purge_auth_sessions() -> int:
    return run_purge_auth_sessions(
        revoked_retention_days=settings.AUTH_SESSION_REVOKED_RETENTION_DAYS,
    )
