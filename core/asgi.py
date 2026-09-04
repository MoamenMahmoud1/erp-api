"""ASGI entry point for the ERP backend.

In production this module is loaded by a proper ASGI server (uvicorn/gunicorn
workers).  The development ``manage.py runserver`` also uses ASGI.

Never use ``manage.py runserver`` in production — see
``deployment/nginx.conf`` and the Dockerfile for the intended gunicorn +
ASGI-worker deployment path.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.settings_dev")

application = get_asgi_application()