from django.db.models import F, Sum, IntegerField
try:
    from django_filters.rest_framework import DjangoFilterBackend
    HAS_DF = True
except Exception:
    HAS_DF = False

from common.mixins import TenantScopedModelViewSet, PrivateTenantOnly
from .models import Warehouse, StockItem, StockLedger, StockReservation
from .serializers import WarehouseSerializer, StockItemSerializer, StockLedgerSerializer, StockReservationSerializer

def _apply_common(qs, request, search_fields=None):
    from commerce.views import _apply_common_query_params
    return _apply_common_query_params(qs, request, search_fields=search_fields)

class WarehouseViewSet(TenantScopedModelViewSet):
    queryset = Warehouse.objects.select_related("store").order_by("name")
    serializer_class = WarehouseSerializer
    permission_classes = [PrivateTenantOnly]
    if HAS_DF:
        filter_backends = [DjangoFilterBackend]
        filterset_fields = ["store", "name"]

    def get_queryset(self):
        return _apply_common(super().get_queryset(), self.request, search_fields=["name"])

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.META.get("HTTP_X_TENANT_ID"))


class StockItemViewSet(TenantScopedModelViewSet):
    """
    Powerful filters:
      ?variant=<uuid>&warehouse=<uuid>
      ?available_gt=0  (available = qty_on_hand - qty_reserved)
      ?ordering=-qty_on_hand
    """
    queryset = StockItem.objects.select_related("warehouse", "variant").order_by("-created_at")
    serializer_class = StockItemSerializer
    permission_classes = [PrivateTenantOnly]
    if HAS_DF:
        filter_backends = [DjangoFilterBackend]
        filterset_fields = ["warehouse", "variant"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.annotate(available=F("qty_on_hand") - F("qty_reserved"))
        qs = _apply_common(qs, self.request)
        # custom numeric filter
        avail_gt = self.request.query_params.get("available_gt")
        if avail_gt is not None:
            try:
                qs = qs.filter(available__gt=int(avail_gt))
            except Exception:
                pass
        return qs

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.META.get("HTTP_X_TENANT_ID"))


class StockLedgerViewSet(TenantScopedModelViewSet):
    queryset = StockLedger.objects.select_related("warehouse", "variant").order_by("-created_at")
    serializer_class = StockLedgerSerializer
    permission_classes = [PrivateTenantOnly]
    if HAS_DF:
        filter_backends = [DjangoFilterBackend]
        filterset_fields = ["variant", "warehouse", "reason", "order_item_id"]

    def get_queryset(self):
        return _apply_common(super().get_queryset(), self.request, search_fields=["reason"])

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.META.get("HTTP_X_TENANT_ID"))


class StockReservationViewSet(TenantScopedModelViewSet):
    queryset = StockReservation.objects.select_related("warehouse", "variant", "order_item").order_by("-created_at")
    serializer_class = StockReservationSerializer
    permission_classes = [PrivateTenantOnly]
    if HAS_DF:
        filter_backends = [DjangoFilterBackend]
        filterset_fields = ["variant", "warehouse", "status", "order_item"]

    def get_queryset(self):
        return _apply_common(super().get_queryset(), self.request, search_fields=["status"])

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.META.get("HTTP_X_TENANT_ID"))
