from rest_framework import serializers
from .models import GatewayAccount, Payment, Refund, Payout

class GatewayAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = GatewayAccount
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = '__all__'

class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = '__all__'
