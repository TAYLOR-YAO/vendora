from rest_framework import serializers
from .models import Plan, Price, Subscription, UsageRecord

class PlanSerializer(serializers.ModelSerializer):
    class Meta: model = Plan; fields = "__all__"

class PriceSerializer(serializers.ModelSerializer):
    class Meta: model = Price; fields = "__all__"

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta: model = Subscription; fields = "__all__"

class UsageRecordSerializer(serializers.ModelSerializer):
    class Meta: model = UsageRecord; fields = "__all__"
