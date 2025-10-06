from rest_framework import serializers
from .models import Shipment, ShipmentItem, PickupCenter


class ShipmentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentItem
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "tenant")


class ShipmentSerializer(serializers.ModelSerializer):
    items = ShipmentItemSerializer(many=True, read_only=True)

    class Meta:
        model = Shipment
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "tenant", "shipped_at", "delivered_at")


class PickupCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupCenter
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "tenant")
