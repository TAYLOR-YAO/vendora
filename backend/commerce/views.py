from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import TenantScopedModelViewSet, AuditedActionsMixin
from common.permissions import ReadPublicWriteAuth
from .models import Product, Variant, Cart, CartItem, Order, OrderItem, Review
from .serializers import (
    ProductListSerializer, ProductDetailSerializer,
    VariantSerializer, CartSerializer, CartItemSerializer,
    OrderSerializer, OrderItemSerializer, ReviewSerializer
)
# adding "AuditedActionsMixin," before "TenantScopedModelViewSet" enables the audit logs

class DefaultPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 200

class ProductViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    """
    Public browse (no tenant) with search/filter/order/pagination.
    Tenant-scoped writes require auth + X-Tenant-ID.
    """
    permission_classes  = [ReadPublicWriteAuth]
    pagination_class    = DefaultPagination
    filter_backends     = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields    = {
        "business": ["exact"],
        "type": ["exact"],
        "is_active": ["exact"],
        "is_public": ["exact"],
        "currency": ["exact"],
        # "category": ["exact"], "subcategory": ["exact"], "industry": ["exact"],  # if enabled
    }
    search_fields       = ["name", "description", "details_json"]
    ordering_fields     = ["created_at", "updated_at", "default_price", "name"]
    ordering            = ["-created_at"]

    queryset = (
        Product.objects
        .select_related("business")
        .prefetch_related("images", "videos", "variants")
    )

    def get_serializer_class(self):
        # List should be light; detail can be nested
        if self.action == "list":
            return ProductListSerializer
        return ProductDetailSerializer

    def public_queryset(self, qs):
        # Public: only show active & public, and published (if tracked)
        qs = qs.filter(is_active=True, is_public=True)
        # Optional published_at gate
        # qs = qs.filter(published_at__isnull=False, published_at__lte=timezone.now())
        return qs

    @method_decorator(cache_page(60 * 5))
    @method_decorator(vary_on_headers("Authorization", "Cookie", "X-Tenant-ID"))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(60 * 5))
    @method_decorator(vary_on_headers("Authorization", "Cookie", "X-Tenant-ID"))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class VariantViewSet(TenantScopedModelViewSet):
    permission_classes = [ReadPublicWriteAuth]
    pagination_class   = DefaultPagination
    filter_backends    = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields   = {"product": ["exact"], "is_active": ["exact"], "sku": ["exact"]}
    search_fields      = ["sku"]
    ordering_fields    = ["created_at", "updated_at", "price", "sku"]
    ordering           = ["-created_at"]

    queryset = Variant.objects.select_related("product")
    serializer_class = VariantSerializer

# adding "AuditedActionsMixin," before "TenantScopedModelViewSet" enables the audit logs
class CartViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    permission_classes = [IsAuthenticated]  # private
    pagination_class   = DefaultPagination
    queryset = Cart.objects.select_related("customer").prefetch_related("items")
    serializer_class = CartSerializer


class CartItemViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    permission_classes = [IsAuthenticated]  # private
    pagination_class   = DefaultPagination
    queryset = CartItem.objects.select_related("variant")
    serializer_class = CartItemSerializer


class OrderViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    permission_classes = [IsAuthenticated]  # private
    pagination_class   = DefaultPagination
    queryset = Order.objects.select_related("business", "customer").prefetch_related("items", "items__variant")
    serializer_class = OrderSerializer


class OrderItemViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    permission_classes = [IsAuthenticated]  # private
    pagination_class   = DefaultPagination
    queryset = OrderItem.objects.select_related("order", "variant")
    serializer_class = OrderItemSerializer


class ReviewViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    # Reads can be public; writes require auth + tenant
    permission_classes = [ReadPublicWriteAuth]
    pagination_class   = DefaultPagination
    queryset = Review.objects.select_related("product")
    serializer_class = ReviewSerializer
