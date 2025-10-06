from django.apps import AppConfig
class ShipmentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shipments"
    def ready(self):
        try:
            from . import signals  # noqa
        except Exception:
            pass
