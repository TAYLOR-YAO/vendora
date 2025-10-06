from rest_framework.permissions import AllowAny
from rest_framework.exceptions import PermissionDenied

try:
    from django_filters.rest_framework import DjangoFilterBackend
    HAS_DF = True
except Exception:
    HAS_DF = False

from common.mixins import TenantScopedModelViewSet, PublicReadTenantOptional, PrivateTenantOnly, AuditedActionsMixin
from .models import Address, Business, Store
from .serializers import AddressSerializer, BusinessSerializer, StoreSerializer
from django.db.models import Q
from . import models as m

def _apply_common(qs, request, search_fields=None):
    from commerce.views import _apply_common_query_params
    return _apply_common_query_params(qs, request, search_fields=search_fields)


class AddressViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    queryset = Address.objects.all().order_by("-created_at")
    serializer_class = AddressSerializer
    permission_classes = [PublicReadTenantOptional]  # public browse address info (ok if non-sensitive)
    if HAS_DF:
        filter_backends = [DjangoFilterBackend]
        filterset_fields = ["city", "country"]

    def get_permissions(self):
        if self.request.method in ("POST", "PUT", "PATCH", "DELETE"):
            return [PrivateTenantOnly()]
        return [p() for p in self.permission_classes]

    def get_queryset(self):
        return _apply_common(super().get_queryset(), self.request, search_fields=["line1", "city", "country"])

    def perform_create(self, serializer):
        tenant_id = self.request.META.get("HTTP_X_TENANT_ID")
        if not tenant_id:
            raise PermissionDenied("X-Tenant-ID required")
        serializer.save(tenant_id=tenant_id)


class BusinessViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    queryset = Business.objects.all().order_by("name")
    serializer_class = BusinessSerializer
    permission_classes = [PublicReadTenantOptional]
    if HAS_DF:
        filter_backends = [DjangoFilterBackend]
        # filterset_fields = ["url_slug", "currency", "allow_backorder"]
        filterset_fields = {
            "slug": ["exact", "in", "icontains"], 
            "is_public": ["exact"],
            "is_active": ["exact"],"currency": ["exact"],
            }
        
    def get_permissions(self):
        if self.request.method in ("POST", "PUT", "PATCH", "DELETE"):
            return [PrivateTenantOnly()]
        return [p() for p in self.permission_classes]

    def get_queryset(self):
        return _apply_common(super().get_queryset(), self.request, search_fields=["name", "url_slug"])

    def perform_create(self, serializer):
        tenant_id = self.request.META.get("HTTP_X_TENANT_ID")
        serializer.save(tenant_id=tenant_id)


class StoreViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    queryset = Store.objects.select_related("business", "address").order_by("name")
    serializer_class = StoreSerializer
    permission_classes = [PublicReadTenantOptional]
    if HAS_DF:
        filter_backends = [DjangoFilterBackend]
        filterset_fields = {"slug": ["exact", "in", "icontains"],
        "type": ["exact", "in"],
        "is_public": ["exact"],
        "is_active": ["exact"],
        "business": ["exact", "in"],
        }

    def get_permissions(self):
        if self.request.method in ("POST", "PUT", "PATCH", "DELETE"):
            return [PrivateTenantOnly()]
        return [p() for p in self.permission_classes]

    def get_queryset(self):
        return _apply_common(super().get_queryset(), self.request, search_fields=["name", "type", "url_slug"])

    def perform_create(self, serializer):
        tenant_id = self.request.META.get("HTTP_X_TENANT_ID")
        serializer.save(tenant_id=tenant_id)
