from django.apps import AppConfig
class PlatformappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "platformapp"
    def ready(self):
        try:
            from . import signals  # noqa
        except Exception:
            pass
