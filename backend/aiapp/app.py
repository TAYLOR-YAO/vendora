from django.apps import AppConfig
class AiAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "aiapp"      # python package path
    label = "aiapp"     # unique app label (keep this one as 'aiapp')
