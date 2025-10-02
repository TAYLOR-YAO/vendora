from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ResourceViewSet
from .views import BookingViewSet

router = DefaultRouter()
router.register(r'resource', ResourceViewSet)
router.register(r'booking', BookingViewSet)

urlpatterns = [ path('', include(router.urls)) ]