from django.apps import AppConfig
class NotificationsappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notificationsapp"
    def ready(self):
        try:
            from . import signals  # noqa
        except Exception:
            pass
