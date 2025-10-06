from django.apps import AppConfig
class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"
    def ready(self):
        try:
            from . import signals  # noqa
        except Exception:
            pass
