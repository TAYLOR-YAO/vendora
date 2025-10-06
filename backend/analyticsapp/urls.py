from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CdpProfileViewSet, EventViewSet,
    RiskSignalViewSet, ModelMetricViewSet
)

router = DefaultRouter()
router.register(r'cdpprofile', CdpProfileViewSet)
router.register(r'event', EventViewSet)
router.register(r'risk-signal', RiskSignalViewSet)    # NEW
router.register(r'model-metric', ModelMetricViewSet)  # NEW

urlpatterns = [path('', include(router.urls))]
