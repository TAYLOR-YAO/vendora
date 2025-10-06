from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    TopicViewSet, NotificationTemplateViewSet, NotificationPreferenceViewSet,
    NotificationDispatchViewSet, NotificationLogViewSet
)

router = DefaultRouter()
router.register(r'topic', TopicViewSet)
router.register(r'template', NotificationTemplateViewSet)
router.register(r'preference', NotificationPreferenceViewSet)
router.register(r'dispatch', NotificationDispatchViewSet)
router.register(r'log', NotificationLogViewSet)

urlpatterns = [path('', include(router.urls))]
