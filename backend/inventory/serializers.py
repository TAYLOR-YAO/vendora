from rest_framework import serializers
from .models import Warehouse, StockItem, StockLedger, StockReservation, StockAdjustment, StockTransfer

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = "__all__"
        read_only_fields = ("tenant","created_at","updated_at")


class StockItemSerializer(serializers.ModelSerializer):
    qty_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = StockItem
        fields = "__all__"
        read_only_fields = ("tenant","qty_reserved","created_at","updated_at","qty_available")

    def validate(self, attrs):
        # Optional extra safety on API writes
        qoh = attrs.get("qty_on_hand", getattr(self.instance, "qty_on_hand", 0))
        qrv = attrs.get("qty_reserved", getattr(self.instance, "qty_reserved", 0))
        if qoh < 0 or qrv < 0 or qrv > qoh:
            raise serializers.ValidationError("Invalid quantities: reserved must be 0..on_hand and non-negative.")
        return attrs


class StockLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockLedger
        fields = "__all__"
        read_only_fields = ("tenant","created_at","updated_at")


class StockReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockReservation
        fields = "__all__"
        read_only_fields = ("tenant","created_at","updated_at")


class StockAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockAdjustment
        fields = "__all__"
        read_only_fields = ("tenant","created_at","updated_at")


class StockTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransfer
        fields = "__all__"
        read_only_fields = ("tenant","created_at","updated_at")
