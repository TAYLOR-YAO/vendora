from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import CdpProfileViewSet
from .views import EventViewSet

router = DefaultRouter()
router.register(r'cdpprofile', CdpProfileViewSet)
router.register(r'event', EventViewSet)

urlpatterns = [ path('', include(router.urls)) ]