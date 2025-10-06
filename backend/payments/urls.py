from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    GatewayAccountViewSet, PaymentViewSet, RefundViewSet, PayoutViewSet,
    InstallmentPlanViewSet, SubscriptionViewSet
)

router = DefaultRouter(trailing_slash=False)
router.register(r'gatewayaccount', GatewayAccountViewSet, basename='gatewayaccount')
router.register(r'payment', PaymentViewSet, basename='payment')
router.register(r'refund', RefundViewSet, basename='refund')
router.register(r'payout', PayoutViewSet, basename='payout')
router.register(r'installmentplan', InstallmentPlanViewSet, basename='installmentplan')
router.register(r'subscription', SubscriptionViewSet, basename='subscription')

urlpatterns = [path('', include(router.urls))]
