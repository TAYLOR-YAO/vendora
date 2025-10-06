from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    healthz, VersionView, TimeView, IPView, EchoView, WhoAmIView, DeepHealthView,
    FeatureFlagViewSet, PublicConfigViewSet, AnnouncementViewSet
)

router = DefaultRouter(trailing_slash=False)
router.register(r'flag', FeatureFlagViewSet, basename="core-flag")
router.register(r'config', PublicConfigViewSet, basename="core-config")
router.register(r'announcement', AnnouncementViewSet, basename="core-announcement")

urlpatterns = [
    path('healthz/', healthz),
    path('version/', VersionView.as_view()),
    path('time/', TimeView.as_view()),
    path('ip/', IPView.as_view()),
    path('echo/', EchoView.as_view()),
    path('whoami/', WhoAmIView.as_view()),
    path('deep-health/', DeepHealthView.as_view()),
    path('', include(router.urls)),
]
