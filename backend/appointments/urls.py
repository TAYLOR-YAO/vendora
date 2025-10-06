from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    ResourceViewSet, ServiceViewSet, ResourceScheduleViewSet, TimeOffViewSet, BookingViewSet
)

router = DefaultRouter()
router.register(r'resource', ResourceViewSet)
router.register(r'service', ServiceViewSet)
router.register(r'schedule', ResourceScheduleViewSet)
router.register(r'timeoff', TimeOffViewSet)
router.register(r'booking', BookingViewSet)

urlpatterns = [path('', include(router.urls))]
