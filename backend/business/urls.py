from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import AddressViewSet
from .views import BusinessViewSet
from .views import StoreViewSet

router = DefaultRouter()
router.register(r'address', AddressViewSet)
router.register(r'business', BusinessViewSet)
router.register(r'store', StoreViewSet)

urlpatterns = [ path('', include(router.urls)) ]