from rest_framework import serializers
from .models import GatewayAccount, Payment, Refund, Payout, InstallmentPlan, Subscription, ProviderEvent


class GatewayAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = GatewayAccount
        fields = "__all__"
        read_only_fields = ("created_at","updated_at")


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ("created_at","updated_at")


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = "__all__"
        read_only_fields = ("created_at","updated_at")


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = "__all__"
        read_only_fields = ("created_at","updated_at")


class InstallmentPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstallmentPlan
        fields = "__all__"
        read_only_fields = ("created_at","updated_at")


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"
        read_only_fields = ("created_at","updated_at")


class ProviderEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderEvent
        fields = "__all__"
        read_only_fields = ("created_at","updated_at")
