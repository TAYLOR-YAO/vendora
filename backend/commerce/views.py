from rest_framework import viewsets
from .models import Product, Variant, Cart, CartItem, Order, OrderItem, Review
from .serializers import ProductSerializer, VariantSerializer, CartSerializer, CartItemSerializer, OrderSerializer, OrderItemSerializer, ReviewSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-id') if hasattr(Product, 'id') else Product.objects.all()
    serializer_class = ProductSerializer

class VariantViewSet(viewsets.ModelViewSet):
    queryset = Variant.objects.all().order_by('-id') if hasattr(Variant, 'id') else Variant.objects.all()
    serializer_class = VariantSerializer

class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all().order_by('-id') if hasattr(Cart, 'id') else Cart.objects.all()
    serializer_class = CartSerializer

class CartItemViewSet(viewsets.ModelViewSet):
    queryset = CartItem.objects.all().order_by('-id') if hasattr(CartItem, 'id') else CartItem.objects.all()
    serializer_class = CartItemSerializer

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-id') if hasattr(Order, 'id') else Order.objects.all()
    serializer_class = OrderSerializer

class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all().order_by('-id') if hasattr(OrderItem, 'id') else OrderItem.objects.all()
    serializer_class = OrderItemSerializer

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all().order_by('-id') if hasattr(Review, 'id') else Review.objects.all()
    serializer_class = ReviewSerializer
