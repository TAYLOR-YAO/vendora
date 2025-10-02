from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import AiModelViewSet
from .views import AiJobViewSet
from .views import AiPredictionViewSet
from .views import AiRecommendationViewSet

router = DefaultRouter()
router.register(r'aimodel', AiModelViewSet)
router.register(r'aijob', AiJobViewSet)
router.register(r'aiprediction', AiPredictionViewSet)
router.register(r'airecommendation', AiRecommendationViewSet)

urlpatterns = [ path('', include(router.urls)) ]