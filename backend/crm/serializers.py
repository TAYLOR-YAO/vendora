from rest_framework import serializers
from .models import Customer, Contact, Pipeline, Opportunity, Activity


# ---- List serializers (fast) ----
class CustomerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id","type","name","email","phone","status","tags","created_at","updated_at")


class OpportunityListSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = ("id","name","amount","currency","stage","probability","expected_close","customer","customer_name","created_at","updated_at")

    def get_customer_name(self, obj):
        return obj.customer.name if obj.customer else None


# ---- Detail serializers (write/read) ----
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ("tenant","consent_ts","created_at","updated_at")


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = "__all__"
        read_only_fields = ("tenant","created_at","updated_at")


class PipelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pipeline
        fields = "__all__"
        read_only_fields = ("tenant","created_at","updated_at")


class OpportunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Opportunity
        fields = "__all__"
        read_only_fields = ("tenant","created_at","updated_at")


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = "__all__"
        read_only_fields = ("tenant","created_at","updated_at")
