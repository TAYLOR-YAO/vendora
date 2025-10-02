from rest_framework import serializers
from .models import AiModel, AiJob, AiPrediction, AiRecommendation

class AiModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiModel
        fields = '__all__'

class AiJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiJob
        fields = '__all__'

class AiPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiPrediction
        fields = '__all__'

class AiRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AiRecommendation
        fields = '__all__'
