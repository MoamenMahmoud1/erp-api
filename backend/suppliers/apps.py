from django.apps import AppConfig


class SuppliersConfig(AppConfig):
    name = 'suppliers'

    def ready(self):
        from . import signals  # noqa: F401
