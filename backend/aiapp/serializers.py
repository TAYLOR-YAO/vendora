from __future__ import annotations
from rest_framework import serializers
from .models import AiModel, AiJob, AiPrediction, AiRecommendation

class AiModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiModel
        fields = "__all__"

class AiJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiJob
        fields = "__all__"
        read_only_fields = ("status","progress","attempts","started_at","finished_at","created_at")

class AiPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiPrediction
        fields = "__all__"
        read_only_fields = ("created_at",)

class AiRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiRecommendation
        fields = "__all__"
        read_only_fields = ("created_at",)
