from django.contrib import admin
from django.apps import apps
from django.contrib.admin.sites import AlreadyRegistered

# The ready() method of the AppConfig is a better place for this,
# but for simplicity and to follow the pattern in other apps,
# we can do it here. This code runs when admin autodiscover runs.
app_config = apps.get_app_config('searchapp')
for model in app_config.get_models():
    try:
        admin.site.register(model)
    except AlreadyRegistered:
        pass