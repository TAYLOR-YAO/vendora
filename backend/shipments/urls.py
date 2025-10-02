from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import PickupCenterViewSet
from .views import ShipmentViewSet

router = DefaultRouter()
router.register(r'pickupcenter', PickupCenterViewSet)
router.register(r'shipment', ShipmentViewSet)

urlpatterns = [ path('', include(router.urls)) ]