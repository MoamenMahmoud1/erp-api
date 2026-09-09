from django.conf import settings
from django.test import SimpleTestCase

from accounting import tasks as accounting_tasks
from core.celery import app
from products import tasks as product_tasks


class CeleryConfigurationTests(SimpleTestCase):
    def test_celery_is_loaded_from_django_settings(self):
        app.autodiscover_tasks(force=True)
        self.assertEqual(app.main, "erp_api")
        self.assertTrue(settings.CELERY_TASK_ALWAYS_EAGER)
        self.assertIsNotNone(accounting_tasks.warm_analytics_reports)
        self.assertIsNotNone(product_tasks.refresh_product_intelligence)
