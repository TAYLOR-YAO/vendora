# invoicing/apps.py
from django.apps import AppConfig

class InvoicingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "invoicing"

    def ready(self):
        from . import signals  # noqa
