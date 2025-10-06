from django.apps import AppConfig

class SearchAppConfig(AppConfig):
    name = "searchapp"
    def ready(self):
        from . import signals  # index hooks
