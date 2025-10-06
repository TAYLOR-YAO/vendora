from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import AddressViewSet, BusinessViewSet, StoreViewSet

router = DefaultRouter()  # keep trailing slash = True to match Django/DRF defaults
router.register(r'address', AddressViewSet, basename="address")
router.register(r'business', BusinessViewSet, basename="business")
router.register(r'store', StoreViewSet, basename="store")

urlpatterns = [path('', include(router.urls))]
