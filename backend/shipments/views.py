from typing import Dict, Any
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils.timezone import now

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers

from common.mixins import TenantScopedModelViewSet
from inventory.models import StockItem, StockLedger, StockReservation
from .models import Shipment, ShipmentItem, PickupCenter
from .serializers import ShipmentSerializer, ShipmentItemSerializer, PickupCenterSerializer


# --- Governance ---
class PrivateReadWrite(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


# --- Utilities ---
def _dec(v) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


# =========================
#      SHIPMENT (private)
# =========================
class ShipmentViewSet(TenantScopedModelViewSet):
    """
    Private API – staff/admin only. Tenant is enforced by TenantScopedModelViewSet.
    """
    queryset = Shipment.objects.select_related("order", "pickup_center", "address").prefetch_related("items")
    serializer_class = ShipmentSerializer
    permission_classes = [PrivateReadWrite]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "status": ["exact", "in"],
        "order_id": ["exact"],
        "carrier": ["exact", "in"],
        "service_level": ["exact", "in"],
        "pickup_center_id": ["exact"],
    }
    search_fields = ["tracking", "carrier", "service_level"]
    ordering_fields = ["created_at", "status", "shipped_at", "delivered_at", "ship_cost"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(tracking__icontains=q) | Q(carrier__icontains=q) | Q(service_level__icontains=q)
            )
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        from django.utils.dateparse import parse_datetime, parse_date
        if start:
            d = parse_datetime(start) or parse_date(start)
            if d:
                qs = qs.filter(created_at__gte=d)
        if end:
            d = parse_datetime(end) or parse_date(end)
            if d:
                qs = qs.filter(created_at__lte=d)
        return qs

    # ---------- Actions ----------
    @action(detail=True, methods=["post"])
    def fulfill(self, request, pk=None):
        """
        Consume stock reservations -> ship items.
        """
        shipment = self.get_object()
        tenant = shipment.tenant

        with transaction.atomic():
            for si in shipment.items.select_related("order_item", "variant").all():
                if si.status == "fulfilled":
                    continue
                remaining = si.qty
                reservations = (
                    StockReservation.objects
                    .select_for_update()
                    .filter(tenant=tenant, order_item=si.order_item, variant=si.variant, status="reserved")
                    .select_related("warehouse")
                    .order_by("created_at")
                )

                for res in reservations:
                    if remaining <= 0:
                        break
                    take = min(res.qty, remaining)

                    stock = StockItem.objects.select_for_update().get(
                        tenant=tenant, warehouse=res.warehouse, variant=si.variant
                    )
                    stock.qty_reserved = max(0, stock.qty_reserved - take)
                    stock.qty_on_hand -= take
                    stock.save(update_fields=["qty_reserved", "qty_on_hand"])

                    StockLedger.objects.create(
                        tenant=tenant, variant=si.variant, qty_delta=-take, reason="consume",
                        warehouse=res.warehouse, order_item_id=si.order_item.id
                    )

                    res.qty -= take
                    res.status = "consumed" if res.qty == 0 else res.status
                    res.save(update_fields=["qty", "status"])
                    remaining -= take

                si.status = "fulfilled"
                si.save(update_fields=["status"])

            shipment.status = "partial" if shipment.items.filter(status="pending").exists() else "fulfilled"
            shipment.shipped_at = now()
            shipment.save(update_fields=["status", "shipped_at"])

        return Response({"ok": True, "shipment": ShipmentSerializer(shipment).data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="bulk-fulfill")
    def bulk_fulfill(self, request):
        """
        Body: {"ids": ["uuid1","uuid2",...]}
        """
        ids = request.data.get("ids") or []
        results = []
        for sid in ids:
            try:
                self.kwargs["pk"] = sid
                resp = self.fulfill(request, sid)
                results.append({"id": sid, "ok": True})
            except Exception as e:
                results.append({"id": sid, "ok": False, "error": str(e)})
        return Response({"results": results})

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        shipment = self.get_object()
        shipment.status = "cancelled"
        shipment.save(update_fields=["status"])
        # TODO: optionally release reservations if any remain
        return Response(ShipmentSerializer(shipment).data)

    @action(detail=True, methods=["post"], url_path="delivered")
    def delivered(self, request, pk=None):
        shipment = self.get_object()
        shipment.status = "delivered"
        shipment.delivered_at = now()
        shipment.save(update_fields=["status", "delivered_at"])
        return Response(ShipmentSerializer(shipment).data)

    # --- Quotes/Labels/Tracking (mocked; wire to real carriers later) ---
    @action(detail=False, methods=["get"], url_path="rate")
    def rate(self, request):
        """
        Example shipping quote:
          ?weight_kg=2.5&service=express&carrier=local-courier
        """
        weight = _dec(request.query_params.get("weight_kg") or "1")
        service = (request.query_params.get("service") or "standard").lower()
        carrier = (request.query_params.get("carrier") or "local-courier").lower()
        base = Decimal("1000")  # base fee XOF
        perkg = Decimal("300")
        if service == "express":
            base += Decimal("800")
        if carrier in ("dhl", "ups"):
            base += Decimal("1200")
        cost = base + perkg * weight
        return Response({"carrier": carrier, "service": service, "weight_kg": str(weight), "cost": str(cost), "currency": "XOF"})

    @action(detail=True, methods=["post"], url_path="label")
    def create_label(self, request, pk=None):
        """
        Create label on provider (mock); store label_url, tracking, tracking_url.
        """
        s = self.get_object()
        s.status = "label_created"
        s.tracking = s.tracking or f"TRK-{s.id.hex[:10].upper()}"
        s.tracking_url = s.tracking_url or f"https://track.example/{s.tracking}"
        s.label_url = s.label_url or f"https://labels.example/{s.id}.pdf"
        s.save(update_fields=["status", "tracking", "tracking_url", "label_url"])
        return Response(ShipmentSerializer(s).data)

    @action(detail=True, methods=["get"], url_path="track")
    def track(self, request, pk=None):
        """
        Mock tracking ping. Real implementation calls carrier API/webhook.
        """
        s = self.get_object()
        stage = s.status
        next_stage = {
            "label_created": "in_transit",
            "in_transit": "delivered",
        }.get(stage)
        eta = s.eta or (now())
        return Response({
            "tracking": s.tracking,
            "status": s.status,
            "eta": eta,
            "tracking_url": s.tracking_url,
            "next_possible_status": next_stage,
        })

    @action(detail=False, methods=["get"], url_path="search_assist")
    def search_assist(self, request):
        """
        Turn rough text into filters. e.g.:
          ?query=in transit last week dhl over 1000
        """
        txt = (request.query_params.get("query") or "").lower()
        filters: Dict[str, Any] = {}
        if "in transit" in txt: filters["status"] = "in_transit"
        if "delivered" in txt: filters["status"] = "delivered"
        if "pending" in txt: filters["status"] = "pending"
        if "dhl" in txt: filters["carrier"] = "dhl"
        if "ups" in txt: filters["carrier"] = "ups"
        if "express" in txt: filters["service_level"] = "express"
        # You can extend with dates/amounts similarly to other apps
        return Response({"filters": filters, "ordering": "-created_at"})
    

# =========================
#  SHIPMENT ITEM (private)
# =========================
class ShipmentItemViewSet(TenantScopedModelViewSet):
    queryset = ShipmentItem.objects.select_related("shipment", "order_item", "variant")
    serializer_class = ShipmentItemSerializer
    permission_classes = [PrivateReadWrite]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {"status": ["exact", "in"], "shipment_id": ["exact"], "variant_id": ["exact"]}
    search_fields = []
    ordering_fields = ["created_at", "status", "qty"]
    ordering = ["-created_at"]
    

# =========================
#  PICKUP CENTER (public read)
# =========================
class PickupCenterViewSet(TenantScopedModelViewSet):
    """
    Public read (no auth), private write/delete.
    The mixin still resolves tenant from header (?tenant_id / ?tenant_slug also supported by your middleware).
    """
    queryset = PickupCenter.objects.all()
    serializer_class = PickupCenterSerializer

    # Allow unauthenticated GET list/retrieve
    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [PrivateReadWrite()]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "code": ["exact", "in"],
        "city": ["exact", "icontains"],
        "country": ["exact"],
    }
    search_fields = ["name", "code", "city"]
    ordering_fields = ["name", "code", "city", "created_at"]
    ordering = ["name"]

    # cache public pickup centers for faster store pages
    @method_decorator(cache_page(60 * 5))
    @method_decorator(vary_on_headers("Authorization", "Cookie"))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(60 * 5))
    @method_decorator(vary_on_headers("Authorization", "Cookie"))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
