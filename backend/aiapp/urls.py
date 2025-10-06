from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import AiModelViewSet, AiJobViewSet, AiPredictionViewSet, AiRecommendationViewSet, provider_webhook
from django.conf import settings
from django.conf.urls.static import static
router = DefaultRouter()
router.register(r'aimodel', AiModelViewSet, basename='aimodel')
router.register(r'aijob', AiJobViewSet, basename='aijob')
router.register(r'aiprediction', AiPredictionViewSet, basename='aiprediction')
router.register(r'airecommendation', AiRecommendationViewSet, basename='airecommendation')

urlpatterns = [
    path('', include(router.urls)),
    path('provider/webhook/', provider_webhook, name='ai_provider_webhook'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
