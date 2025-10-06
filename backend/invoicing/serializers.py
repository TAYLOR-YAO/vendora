from rest_framework import serializers
from .models import TaxRate, Invoice


class TaxRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxRate
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class InvoiceSerializer(serializers.ModelSerializer):
    """
    Write: You set order, number (optional), notes, due_date, etc.
    Money snapshot fields are writable so you can set them from order or a service.
    """
    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")
