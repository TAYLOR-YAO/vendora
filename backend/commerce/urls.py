from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ProductViewSet
from .views import VariantViewSet
from .views import CartViewSet
from .views import CartItemViewSet
from .views import OrderViewSet
from .views import OrderItemViewSet
from .views import ReviewViewSet

router = DefaultRouter()
router.register(r'product', ProductViewSet)
router.register(r'variant', VariantViewSet)
router.register(r'cart', CartViewSet)
router.register(r'cartitem', CartItemViewSet)
router.register(r'order', OrderViewSet)
router.register(r'orderitem', OrderItemViewSet)
router.register(r'review', ReviewViewSet)

urlpatterns = [ path('', include(router.urls)) ]