# generated below
from rest_framework import serializers
from .models import FeatureFlag, PublicConfig, Announcement


class FeatureFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureFlag
        fields = "__all__"


class PublicConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicConfig
        fields = "__all__"


class AnnouncementSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Announcement
        fields = "__all__"
