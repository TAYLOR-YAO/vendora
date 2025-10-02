from rest_framework import viewsets
from .models import AiModel, AiJob, AiPrediction, AiRecommendation
from .serializers import AiModelSerializer, AiJobSerializer, AiPredictionSerializer, AiRecommendationSerializer

class AiModelViewSet(viewsets.ModelViewSet):
    queryset = AiModel.objects.all().order_by('-id') if hasattr(AiModel, 'id') else AiModel.objects.all()
    serializer_class = AiModelSerializer

class AiJobViewSet(viewsets.ModelViewSet):
    queryset = AiJob.objects.all().order_by('-id') if hasattr(AiJob, 'id') else AiJob.objects.all()
    serializer_class = AiJobSerializer

class AiPredictionViewSet(viewsets.ModelViewSet):
    queryset = AiPrediction.objects.all().order_by('-id') if hasattr(AiPrediction, 'id') else AiPrediction.objects.all()
    serializer_class = AiPredictionSerializer

class AiRecommendationViewSet(viewsets.ModelViewSet):
    queryset = AiRecommendation.objects.all().order_by('-id') if hasattr(AiRecommendation, 'id') else AiRecommendation.objects.all()
    serializer_class = AiRecommendationSerializer
