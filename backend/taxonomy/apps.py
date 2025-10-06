from django.apps import AppConfig
class TaxonomyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "taxonomy"
    def ready(self):
        try:
            from . import signals  # noqa
        except Exception:
            pass
