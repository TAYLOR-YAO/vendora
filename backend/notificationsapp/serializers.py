from rest_framework import serializers
from .models import NotificationTemplate, NotificationPreference, NotificationDispatch, NotificationLog

class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = '__all__'

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = '__all__'

class NotificationDispatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationDispatch
        fields = '__all__'

class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = '__all__'
