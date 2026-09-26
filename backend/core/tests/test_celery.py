from django.conf import settings
from django.test import SimpleTestCase

from core.celery import app


class CeleryConfigurationTests(SimpleTestCase):
    def test_celery_is_loaded_from_django_settings(self):
        app.autodiscover_tasks(force=True)
        self.assertEqual(app.main, "erp_api")
        self.assertEqual(app.conf.broker_url, settings.CELERY_BROKER_URL)

    def test_celery_uses_database_beat_scheduler(self):
        self.assertEqual(
            settings.CELERY_BEAT_SCHEDULER,
            "django_celery_beat.schedulers:DatabaseScheduler",
        )
        self.assertEqual(
            app.conf.beat_scheduler,
            settings.CELERY_BEAT_SCHEDULER,
        )
        self.assertFalse(hasattr(settings, "CELERY_BEAT_SCHEDULE"))
