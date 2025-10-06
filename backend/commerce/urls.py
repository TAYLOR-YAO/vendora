from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    ProductViewSet, VariantViewSet, CartViewSet, CartItemViewSet,
    OrderViewSet, OrderItemViewSet, ReviewViewSet
)

# Let DRF default to trailing slash to match Django’s patterns
router = DefaultRouter()  # trailing_slash=True (default)
router.register(r'product',   ProductViewSet,  basename='product')
router.register(r'variant',   VariantViewSet,  basename='variant')
router.register(r'cart',      CartViewSet,     basename='cart')
router.register(r'cartitem',  CartItemViewSet, basename='cartitem')
router.register(r'order',     OrderViewSet,    basename='order')
router.register(r'orderitem', OrderItemViewSet,basename='orderitem')
router.register(r'review',    ReviewViewSet,   basename='review')

urlpatterns = [ path('', include(router.urls)) ]
