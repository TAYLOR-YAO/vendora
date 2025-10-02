from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import GatewayAccountViewSet
from .views import PaymentViewSet
from .views import RefundViewSet
from .views import PayoutViewSet

router = DefaultRouter()
router.register(r'gatewayaccount', GatewayAccountViewSet)
router.register(r'payment', PaymentViewSet)
router.register(r'refund', RefundViewSet)
router.register(r'payout', PayoutViewSet)

urlpatterns = [ path('', include(router.urls)) ]