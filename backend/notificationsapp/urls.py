from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import NotificationTemplateViewSet
from .views import NotificationPreferenceViewSet
from .views import NotificationDispatchViewSet
from .views import NotificationLogViewSet

router = DefaultRouter()
router.register(r'notificationtemplate', NotificationTemplateViewSet)
router.register(r'notificationpreference', NotificationPreferenceViewSet)
router.register(r'notificationdispatch', NotificationDispatchViewSet)
router.register(r'notificationlog', NotificationLogViewSet)

urlpatterns = [ path('', include(router.urls)) ]