from django.apps import AppConfig
class HrConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hr"
    def ready(self):
        try:
            from . import signals  # noqa
        except Exception:
            pass
