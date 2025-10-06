# This file was auto-generated as a scaffold.
# SAFE to edit. Keep functions/class names if you rely on them across apps.

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Example routes (uncomment when you add a ViewSet)
# from .views import ModelNameViewSet
from .views import HealthView

app_name = __package__.split('.')[0]
router = DefaultRouter()
# router.register(r'modelname', ModelNameViewSet)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("", include(router.urls)),
]
