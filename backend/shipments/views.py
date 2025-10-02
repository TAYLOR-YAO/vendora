from rest_framework import viewsets
from .models import PickupCenter, Shipment
from .serializers import PickupCenterSerializer, ShipmentSerializer

class PickupCenterViewSet(viewsets.ModelViewSet):
    queryset = PickupCenter.objects.all().order_by('-id') if hasattr(PickupCenter, 'id') else PickupCenter.objects.all()
    serializer_class = PickupCenterSerializer

class ShipmentViewSet(viewsets.ModelViewSet):
    queryset = Shipment.objects.all().order_by('-id') if hasattr(Shipment, 'id') else Shipment.objects.all()
    serializer_class = ShipmentSerializer
