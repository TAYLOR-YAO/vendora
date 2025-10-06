from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ShipmentViewSet, ShipmentItemViewSet, PickupCenterViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'shipment', ShipmentViewSet, basename='shipment')
router.register(r'shipmentitem', ShipmentItemViewSet, basename='shipmentitem')
router.register(r'pickupcenter', PickupCenterViewSet, basename='pickupcenter')

urlpatterns = [path('', include(router.urls))]
