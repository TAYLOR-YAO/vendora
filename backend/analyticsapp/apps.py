from django.apps import AppConfig
class AnalyticsappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "analyticsapp"
    def ready(self):
        try:
            from . import signals  # noqa
        except Exception:
            pass
