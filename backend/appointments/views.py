from datetime import datetime, timedelta
from typing import List, Dict

from django.utils import timezone
from django.db.models import Q
from django.utils.dateparse import parse_datetime

from rest_framework import permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import TenantScopedModelViewSet
from platformapp.permissions import IsTenantOperatorOrAdmin

from .models import Resource, Service, ResourceSchedule, TimeOff, Booking
from .serializers import (
    ResourceSerializer, ServiceSerializer, ResourceScheduleSerializer,
    TimeOffSerializer, BookingSerializer
)


READ_FILTERS = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


def _apply_q(request, qs, fields):
    q = request.query_params.get("q")
    if not q:
        return qs
    cond = Q()
    for f in fields:
        cond |= Q(**{f"{f}__icontains": q})
    return qs.filter(cond)


# ---------- Resources ----------
class ResourceViewSet(TenantScopedModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [permissions.AllowAny]  # public read; writes require operator
    filter_backends = READ_FILTERS
    search_fields = ["name", "type", "location", "skills"]
    ordering_fields = ["name", "type", "is_active", "created_at"]
    filterset_fields = ["type", "is_active", "capacity"]

    def get_permissions(self):
        if self.request.method in ("POST", "PUT", "PATCH", "DELETE"):
            return [IsTenantOperatorOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        return _apply_q(self.request, super().get_queryset(), self.search_fields)

    @action(detail=True, methods=["get"], url_path="availability", permission_classes=[permissions.AllowAny])
    def availability(self, request, pk=None):
        """
        ?from=2025-10-05T08:00:00Z&to=2025-10-05T18:00:00Z&service_id=<uuid>&step_min=15
        Returns free slots [(start,end), ...] considering:
          - schedules
          - time-offs
          - existing bookings vs capacity
          - service duration + buffers
        """
        resource = self.get_object()
        tenant = self.get_tenant(request)

        start = parse_datetime(request.query_params.get("from") or "")
        end = parse_datetime(request.query_params.get("to") or "")
        service_id = request.query_params.get("service_id")
        step_min = int(request.query_params.get("step_min") or "15")

        if not (start and end and service_id):
            return Response({"detail": "from, to, and service_id are required"}, status=400)
        if end <= start:
            return Response({"detail": "Invalid time range"}, status=400)

        service = Service.objects.filter(tenant=tenant, id=service_id, is_active=True).first()
        if not service:
            return Response({"detail": "Service not found"}, status=404)

        dur = timedelta(minutes=service.duration_min + service.buffer_after_min)
        buf_before = timedelta(minutes=service.buffer_before_min)

        # Build candidate start times respecting schedules
        slots: List[Dict] = []
        cursor = start
        while cursor + dur <= end:
            # Schedule window check
            weekday = cursor.weekday()
            wins = list(resource.schedules.filter(weekday=weekday))
            if wins:
                lt = timezone.localtime(cursor).time()
                lt_end = (timezone.localtime(cursor + dur)).time()
                inside = any(w.start_time <= lt and lt_end <= w.end_time for w in wins)
                if not inside:
                    cursor += timedelta(minutes=step_min)
                    continue

            # Time-off collision
            if resource.timeoffs.filter(start_at__lt=cursor + dur, end_at__gt=cursor).exists():
                cursor += timedelta(minutes=step_min)
                continue

            # Capacity check
            overlapping = Booking.objects.filter(
                tenant=tenant,
                resource=resource,
                status__in=["booked", "confirmed"],
                start_at__lt=cursor + dur,
                end_at__gt=cursor - buf_before,
            ).count()
            if overlapping < resource.capacity:
                slots.append({
                    "start": cursor.isoformat(),
                    "end": (cursor + dur).isoformat(),
                })

            cursor += timedelta(minutes=step_min)

        return Response({"resource_id": str(resource.id), "service_id": str(service.id), "slots": slots})


# ---------- Services ----------
class ServiceViewSet(TenantScopedModelViewSet):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]  # public read
    filter_backends = READ_FILTERS
    search_fields = ["name", "description"]
    ordering_fields = ["name", "duration_min", "price", "created_at"]
    filterset_fields = ["is_active"]

    def get_permissions(self):
        if self.request.method in ("POST", "PUT", "PATCH", "DELETE"):
            return [IsTenantOperatorOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("resources")
        resource_id = self.request.query_params.get("resource")
        if resource_id:
            qs = qs.filter(resources__id=resource_id)
        return _apply_q(self.request, qs, self.search_fields)


# ---------- Schedules & TimeOff ----------
class ResourceScheduleViewSet(TenantScopedModelViewSet):
    queryset = ResourceSchedule.objects.all()
    serializer_class = ResourceScheduleSerializer
    permission_classes = [IsTenantOperatorOrAdmin]
    filter_backends = READ_FILTERS
    search_fields = []
    ordering_fields = ["weekday", "start_time", "end_time"]
    filterset_fields = ["resource", "weekday"]


class TimeOffViewSet(TenantScopedModelViewSet):
    queryset = TimeOff.objects.all()
    serializer_class = TimeOffSerializer
    permission_classes = [IsTenantOperatorOrAdmin]
    filter_backends = READ_FILTERS
    search_fields = ["reason"]
    ordering_fields = ["start_at", "end_at", "created_at"]
    filterset_fields = ["resource"]


# ---------- Bookings ----------
class BookingViewSet(TenantScopedModelViewSet):
    queryset = Booking.objects.select_related("resource", "service", "customer").order_by("-start_at")
    serializer_class = BookingSerializer
    # Public can search availability; creation may be allowed for customers (unauth),
    # but updating/cancelling is usually authenticated or operator-only.
    permission_classes = [permissions.AllowAny]
    filter_backends = READ_FILTERS
    search_fields = ["notes", "status", "source"]
    ordering_fields = ["start_at", "status", "created_at"]
    filterset_fields = ["resource", "service", "status", "customer"]

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            # staff/operator/admin only
            return [IsTenantOperatorOrAdmin()]
        # Allow anyone to create a booking (you can tighten to Auth if needed)
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        # Range filters
        start_gte = self.request.query_params.get("start_gte")
        start_lte = self.request.query_params.get("start_lte")
        if start_gte:
            qs = qs.filter(start_at__gte=parse_datetime(start_gte))
        if start_lte:
            qs = qs.filter(start_at__lte=parse_datetime(start_lte))
        return _apply_q(self.request, qs, self.search_fields)

    @action(detail=True, methods=["post"], url_path="confirm", permission_classes=[IsTenantOperatorOrAdmin])
    def confirm(self, request, pk=None):
        b = self.get_object()
        if b.status not in ("booked",):
            return Response({"detail": "Cannot confirm from current status."}, status=400)
        b.status = "confirmed"
        b.save(update_fields=["status"])
        return Response({"ok": True})

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """
        Allow customer (if you pass a code or own user) or staff to cancel.
        Here we keep it open; you can add verification.
        """
        b = self.get_object()
        if b.status in ("completed", "cancelled", "no_show"):
            return Response({"detail": "Already finalized."}, status=400)
        b.status = "cancelled"
        b.cancelled_at = timezone.now()
        b.cancelled_by_user_id = getattr(request.user, "id", None)
        b.cancellation_reason = request.data.get("reason") or b.cancellation_reason
        b.save(update_fields=["status", "cancelled_at", "cancelled_by_user_id", "cancellation_reason"])
        return Response({"ok": True})

    @action(detail=True, methods=["post"], url_path="reschedule", permission_classes=[permissions.AllowAny])
    def reschedule(self, request, pk=None):
        """
        Body: {"start_at": "...", "end_at": "..."} or {"start_at": "...", "service": "<uuid>"}.
        Uses serializer validation for conflicts.
        """
        old = self.get_object()
        if old.status in ("completed", "cancelled", "no_show"):
            return Response({"detail": "Cannot reschedule a finalized booking."}, status=400)

        data = {
            "tenant": old.tenant_id,
            "resource": old.resource_id,
            "service": request.data.get("service", old.service_id),
            "customer": old.customer_id,
            "start_at": request.data.get("start_at"),
            "end_at": request.data.get("end_at"),
            "status": "booked",
            "notes": old.notes,
            "price": old.price,
            "currency": old.currency,
            "reschedule_of": old.id,
            "source": "web",
        }
        ser = BookingSerializer(data=data, context={"tenant": old.tenant})
        ser.is_valid(raise_exception=True)
        new_b = ser.save(tenant=old.tenant)

        # cancel old
        old.status = "cancelled"
        old.cancelled_at = timezone.now()
        old.save(update_fields=["status", "cancelled_at"])

        return Response({"ok": True, "booking": BookingSerializer(new_b).data})
