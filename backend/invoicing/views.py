from datetime import datetime
from typing import Dict, Any

from django.db.models import Q
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.timezone import make_aware

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import TenantScopedModelViewSet
from .models import TaxRate, Invoice
from .serializers import TaxRateSerializer, InvoiceSerializer


# ---------- Permissions that match your governance ----------

class PublicRead_TenantWrite(permissions.BasePermission):
    """
    SAFE_METHODS: allow anyone (no tenant header required)
    MUTATING methods: require authenticated + tenant header (enforced by TenantScopedModelViewSet).
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)


class PrivateReadWrite(permissions.BasePermission):
    """
    All access requires authentication for invoices (private documents).
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


# ---------- TaxRate (public read; tenant gated writes) ----------

class TaxRateViewSet(TenantScopedModelViewSet):
    queryset = TaxRate.objects.all().order_by("country", "name")
    serializer_class = TaxRateSerializer
    permission_classes = [PublicRead_TenantWrite]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "country": ["exact", "in"],
        "name": ["exact", "icontains"],
        "rate": ["exact", "gte", "lte"],
    }
    search_fields = ["country", "name"]
    ordering_fields = ["country", "name", "rate", "created_at"]
    ordering = ["country", "name"]


# ---------- Invoice (private) with dynamic filters + AI-ish search assist ----------

class InvoiceViewSet(TenantScopedModelViewSet):
    """
    Private (auth-only). Flexible filter/search for UI & integrators:
    - q: searches number, billing fields
    - status: open|sent|paid|void|overdue (supports comma list)
    - min_total/max_total
    - start/end date (issued_at)
    - due_before/due_after
    - order_id exact
    - currency exact
    """
    queryset = Invoice.objects.select_related("order").order_by("-issued_at")
    serializer_class = InvoiceSerializer
    permission_classes = [PrivateReadWrite]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    # allow direct filter fields (DjangoFilter)
    filterset_fields = {
        "status": ["exact", "in"],
        "currency": ["exact"],
        "order_id": ["exact"],
    }
    # full-text-ish search (DB-dependent)
    search_fields = ["number", "billing_name", "billing_email", "notes"]
    ordering_fields = ["issued_at", "due_date", "total_amount", "status", "number"]
    ordering = ["-issued_at"]

    # ---- optional: soft guard for tenant header on writes is already in TenantScopedModelViewSet ----

    def get_queryset(self):
        qs = super().get_queryset()  # TenantScopedModelViewSet will restrict on writes; reads remain tenant-agnostic logic here
        # Apply dynamic query params
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(number__icontains=q)
                | Q(billing_name__icontains=q)
                | Q(billing_email__icontains=q)
                | Q(notes__icontains=q)
            )

        def _dec(v, field):
            try:
                from decimal import Decimal
                return Decimal(v)
            except Exception:
                return None

        min_total = _dec(self.request.query_params.get("min_total"), "min_total")
        max_total = _dec(self.request.query_params.get("max_total"), "max_total")
        if min_total is not None:
            qs = qs.filter(total_amount__gte=min_total)
        if max_total is not None:
            qs = qs.filter(total_amount__lte=max_total)

        def _dt(key):
            raw = self.request.query_params.get(key)
            if not raw:
                return None
            # accept full ISO or YYYY-MM-DD
            dt = parse_datetime(raw)
            if dt:
                return make_aware(dt) if dt.tzinfo is None else dt
            d = parse_date(raw)
            if d:
                return make_aware(datetime(d.year, d.month, d.day))
            return None

        start = _dt("start")       # issued_at >= start
        end = _dt("end")           # issued_at <= end
        if start:
            qs = qs.filter(issued_at__gte=start)
        if end:
            qs = qs.filter(issued_at__lte=end)

        due_before = _dt("due_before")
        due_after = _dt("due_after")
        if due_before:
            qs = qs.filter(due_date__lte=due_before)
        if due_after:
            qs = qs.filter(due_date__gte=due_after)

        statuses = self.request.query_params.get("statuses")
        if statuses:
            qs = qs.filter(status__in=[s.strip() for s in statuses.split(",") if s.strip()])

        return qs

    # --------- AI-ish helper to translate natural language → filters ----------
    @action(detail=False, methods=["GET"], url_path="search_assist", permission_classes=[PrivateReadWrite])
    def search_assist(self, request):
        """
        Example:
        /api/v1/invoicing/invoice/search_assist/?query=paid last month over 100
        Returns a filter payload the UI can reuse.
        """
        text = (request.query_params.get("query") or "").lower()

        filters: Dict[str, Any] = {}
        ordering = "-issued_at"

        # naive parsing (extensible later)
        if "paid" in text:
            filters["status"] = "paid"
        if "open" in text:
            filters["status"] = "open"
        if "overdue" in text:
            filters["status"] = "overdue"

        from datetime import timedelta
        from django.utils import timezone

        now = timezone.now()
        if "last month" in text:
            start = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
            end = now.replace(day=1) - timedelta(seconds=1)
            filters["start"] = start.date().isoformat()
            filters["end"] = end.date().isoformat()

        # totals
        import re
        over = re.search(r"over\s+(\d+(\.\d+)?)", text)
        under = re.search(r"under\s+(\d+(\.\d+)?)", text)
        if over:
            filters["min_total"] = over.group(1)
        if under:
            filters["max_total"] = under.group(1)

        return Response({"filters": filters, "ordering": ordering})
