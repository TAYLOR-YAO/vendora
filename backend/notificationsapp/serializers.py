from rest_framework import serializers
from .models import (
    Topic, NotificationTemplate, NotificationPreference, NotificationDispatch, NotificationLog
)

class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")

class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")

class NotificationDispatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationDispatch
        fields = "__all__"
        read_only_fields = ("tenant", "status", "created_at", "sent_at", "provider_ref",)

class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = "__all__"
        read_only_fields = ("tenant", "created_at")
