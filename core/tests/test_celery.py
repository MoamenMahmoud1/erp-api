from django.conf import settings
from django.test import SimpleTestCase

from core.celery import app


class CeleryConfigurationTests(SimpleTestCase):
    def test_celery_is_loaded_from_django_settings(self):
        app.autodiscover_tasks(force=True)
        self.assertEqual(app.main, "erp_api")
        self.assertEqual(app.conf.broker_url, settings.CELERY_BROKER_URL)

    def test_expected_background_tasks_are_scheduled(self):
        schedule = settings.CELERY_BEAT_SCHEDULE
        self.assertEqual(
            set(schedule),
            {
                "reconcile-company-counters",
                "rebuild-recent-approval-notifications",
            },
        )
        self.assertEqual(
            schedule["reconcile-company-counters"]["task"],
            "organization.tasks.reconcile_company_counters",
        )
        self.assertEqual(
            schedule["rebuild-recent-approval-notifications"]["task"],
            "notifications.tasks.rebuild_recent_approval_notifications",
        )
