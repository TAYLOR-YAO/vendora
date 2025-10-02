from rest_framework import serializers
from .models import PickupCenter, Shipment

class PickupCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupCenter
        fields = '__all__'

class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = '__all__'
