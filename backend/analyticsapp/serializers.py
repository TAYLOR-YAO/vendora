from rest_framework import serializers
from .models import CdpProfile, Event

class CdpProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CdpProfile
        fields = '__all__'

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'
