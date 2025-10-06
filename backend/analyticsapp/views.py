from __future__ import annotations
from typing import Any, Dict, List
from django.db.models import Count, F
from django.utils import timezone
from rest_framework import status, permissions, mixins, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from common.mixins import TenantScopedModelViewSet, PublicListNoTenantMixin
from platformapp.models import Tenant
from .models import CdpProfile, Event, RiskSignal, ModelMetric, DeviceFingerprint
from .serializers import CdpProfileSerializer, EventSerializer, RiskSignalSerializer, ModelMetricSerializer, DeviceFingerprintSerializer
from .filters import EventSmartFilter
from .utils import resolve_profile_for_ingest

# ---------- Governance ----------
# Public ingestion: anyone can POST events for a tenant slug or X-Tenant header.
class IngestPermission(permissions.AllowAny):
    pass

# Read: operators/admins get full power; public can read only if tenant allows (flag you manage on Tenant or Business).
class PublicReadOrOperator(permissions.BasePermission):
    def has_permission(self, request, view):
        # Example: allow GET if ?public=1 and tenant.status == "active"
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


# ---------- Profiles ----------
class CdpProfileViewSet(TenantScopedModelViewSet):
    queryset = CdpProfile.objects.all().order_by("-created_at")
    serializer_class = CdpProfileSerializer

    filterset_fields = {
        "customer": ["exact", "isnull"],
        "created_at": ["gte", "lte"],
    }
    search_fields = ["traits_json", "customer__name"]


# ---------- Events ----------
class EventViewSet(TenantScopedModelViewSet):
    """
    Authenticated tenant-scoped management of events (admins/operators).
    For flexible querying from UI. Use /ingest/ for public write.
    """
    queryset = Event.objects.all().order_by("-ts")
    serializer_class = EventSerializer
    filter_backends = [EventSmartFilter]
    # No default filterset_fields (EventSmartFilter handles it)

    @action(detail=False, methods=["get"], permission_classes=[PublicReadOrOperator])
    def quick_stats(self, request, *args, **kwargs):
        """
        Small, fast aggregates (for dashboards):
          - total events
          - top events by name (limit N)
          - events per day (last 30d)
        """
        tenant = self.get_tenant(request)
        limit = int(request.query_params.get("limit", "10"))

        base = Event.objects.filter(tenant=tenant)
        total = base.count()

        top = (
            base.values("name")
            .annotate(c=Count("id"))
            .order_by("-c")[:limit]
        )

        since = timezone.now() - timezone.timedelta(days=30)
        per_day = (
            base.filter(ts__gte=since)
            .extra(select={"d": "date(ts)"})
            .values("d")
            .annotate(c=Count("id"))
            .order_by("d")
        )

        return Response({
            "total": total,
            "top": list(top),
            "per_day": list(per_day),
        })

    @action(detail=False, methods=["post"], url_path="ingest", permission_classes=[IngestPermission])
    def ingest(self, request, *args, **kwargs):
        """
        Public ingestion endpoint (no auth) with tenant resolution via:
          - X-Tenant: <tenant-slug>  (preferred)
          - ?tenant=<slug>
        Body supports list (batch) or single event.
        """
        slug = request.headers.get("X-Tenant") or request.query_params.get("tenant")
        if not slug:
            return Response({"detail": "tenant slug required (X-Tenant or ?tenant=)"}, status=400)

        tenant = Tenant.objects.filter(slug=slug, status="active").first()
        if not tenant:
            return Response({"detail": "tenant not found or inactive"}, status=404)

        payload = request.data
        if isinstance(payload, dict):
            items = [payload]
        elif isinstance(payload, list):
            items = payload
        else:
            return Response({"detail": "invalid payload"}, status=400)

        created = 0
        out_ids: List[int] = []
        for it in items:
            try:
                name = it.get("name") or "track"
                props = it.get("props") or {}
                session_id = it.get("session_id")
                device_id = it.get("device_id")
                user_id = it.get("user_id")
                client_ts = it.get("client_ts")

                profile = resolve_profile_for_ingest(tenant, {
                    "traits": it.get("traits") or {},
                    "device_id": device_id,
                    "user_id": user_id,
                })

                ev = Event.objects.create(
                    tenant=tenant,
                    profile=profile,
                    name=name,
                    props=props,
                    session_id=session_id,
                    device_id=device_id,
                    user_id=user_id,
                    client_ts=client_ts,
                )
                created += 1
                out_ids.append(ev.id)
            except Exception as e:
                # Be resilient—continue batch
                continue

        return Response({"ok": True, "created": created, "ids": out_ids}, status=status.HTTP_201_CREATED)

    # Example analysis endpoints (quick, UI-friendly)
    @action(detail=False, methods=["get"], permission_classes=[PublicReadOrOperator])
    def top_products(self, request):
        """
        Counts events where props.product_id present (e.g., 'product_view', 'add_to_cart').
        ?name=product_view,add_to_cart&since=<iso>&limit=10
        """
        tenant = self.get_tenant(request)
        p = request.query_params
        limit = int(p.get("limit", "10"))
        names = [n.strip() for n in (p.get("name") or "product_view").split(",") if n.strip()]
        qs = (Event.objects
              .filter(tenant=tenant, name__in=names)
              .exclude(props__product_id=None)
              .values(pid=F("props__product_id"))
              .annotate(c=Count("id"))
              .order_by("-c")[:limit])
        return Response(list(qs))

    @action(detail=False, methods=["get"], permission_classes=[PublicReadOrOperator])
    def funnel(self, request):
        """
        Naive funnel (stage1 -> stage2 -> stage3) by session:
          ?steps=product_view,add_to_cart,checkout_started
          Returns counts per step and drop-offs.
        """
        tenant = self.get_tenant(request)
        steps = [s.strip() for s in (request.query_params.get("steps") or "").split(",") if s.strip()]
        if not steps:
            return Response({"detail": "steps required"}, status=400)

        base = Event.objects.filter(tenant=tenant, name__in=steps)
        by_session = {}
        for e in base.values("session_id", "name"):
            sid = e["session_id"] or "na"
            by_session.setdefault(sid, set()).add(e["name"])

        counts = []
        prev_sessions = set(by_session.keys())
        for s in steps:
            has_s = {sid for sid, names in by_session.items() if s in names}
            counts.append({"step": s, "count": len(has_s)})
            prev_sessions = prev_sessions & has_s

        return Response({"steps": counts})

# RiskSignal (tenant required; not public)
class RiskSignalViewSet(TenantScopedModelViewSet):
    queryset = RiskSignal.objects.all().order_by("-created_at")
    serializer_class = RiskSignalSerializer

    search_fields = ("tx_id", "channel", "country")
    ordering_fields = ("created_at", "amount", "score")

    @action(detail=False, methods=["get"])
    def stats(self, request, *args, **kwargs):
        """Quick counts by label for dashboards."""
        qs = self.get_queryset()
        return Response({
            "total": qs.count(),
            "labeled": qs.exclude(y_label__isnull=True).count(),
            "fraud": qs.filter(y_label=1).count(),
            "legit": qs.filter(y_label=0).count(),
        })


# Metrics snapshots (optional)
class ModelMetricViewSet(TenantScopedModelViewSet):
    queryset = ModelMetric.objects.all().order_by("-created_at")
    serializer_class = ModelMetricSerializer

    search_fields = ("model_key", "slice_key")
    ordering_fields = ("created_at", "auc", "pr_auc")


class DeviceFingerprintViewSet(TenantScopedModelViewSet):
    queryset = DeviceFingerprint.objects.all().order_by("-last_seen")
    serializer_class = DeviceFingerprintSerializer

    search_fields = ("device_id",)
    ordering_fields = ("last_seen", "risk_score")