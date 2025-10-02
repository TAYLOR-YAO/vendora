from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import SegmentViewSet
from .views import CampaignViewSet

router = DefaultRouter()
router.register(r'segment', SegmentViewSet)
router.register(r'campaign', CampaignViewSet)

urlpatterns = [ path('', include(router.urls)) ]