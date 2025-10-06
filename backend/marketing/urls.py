from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    SegmentViewSet, CampaignViewSet, CampaignSendViewSet, CampaignEventViewSet
)

router = DefaultRouter()
router.register(r'segment', SegmentViewSet, basename='segment')
router.register(r'campaign', CampaignViewSet, basename='campaign')
router.register(r'send', CampaignSendViewSet, basename='campaignsend')
router.register(r'event', CampaignEventViewSet, basename='campaignevent')

urlpatterns = [path('', include(router.urls))]
