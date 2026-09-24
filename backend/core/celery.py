"""Celery application for background ERP analytics and intelligence jobs."""

import os

from celery import Celery

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "core.settings.settings_dev",
)

app = Celery("erp_api")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
