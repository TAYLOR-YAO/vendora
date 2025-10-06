from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import PlanViewSet, PriceViewSet, SubscriptionViewSet

router = DefaultRouter()
router.register(r'plan', PlanViewSet)
router.register(r'price', PriceViewSet)
router.register(r'subscription', SubscriptionViewSet)

urlpatterns = [path('', include(router.urls))]
