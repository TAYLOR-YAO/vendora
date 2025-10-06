from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from rest_framework import serializers

from .models import Resource, Service, ResourceSchedule, TimeOff, Booking


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")


class ResourceScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceSchedule
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")


class TimeOffSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeOff
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at", "cancelled_at")

    def validate(self, data):
        """
        Conflict checks:
        - resource active
        - within schedule
        - not colliding with time-off
        - not overlapping existing bookings beyond capacity
        - compute end_at if service provided and end_at missing
        """
        tenant = self.context.get("tenant")
        instance = getattr(self, "instance", None)
        resource = data.get("resource") or (instance.resource if instance else None)
        service = data.get("service") or (instance.service if instance else None)
        start_at = data.get("start_at") or (instance.start_at if instance else None)
        end_at = data.get("end_at") or (instance.end_at if instance else None)

        if not resource or not start_at:
            raise serializers.ValidationError("resource and start_at are required")

        if service and not end_at:
            dur = service.duration_min or 30
            buf_before = service.buffer_before_min or 0
            buf_after = service.buffer_after_min or 0
            start_at = start_at - timedelta(minutes=buf_before)
            end_at = (data.get("start_at") or instance.start_at) + timedelta(minutes=dur + buf_after)
            data["start_at"] = start_at
            data["end_at"] = end_at

        if not end_at:
            raise serializers.ValidationError("end_at is required if service is not provided")

        # Resource must be active
        if not resource.is_active:
            raise serializers.ValidationError("Resource is not active")

        # Basic schedule check (weekday/time window)
        weekday = start_at.weekday()
        has_window = resource.schedules.filter(weekday=weekday).exists()
        if has_window:
            # If there are schedules for that weekday, enforce the window
            inside = False
            local_start = timezone.localtime(start_at).time()
            local_end = timezone.localtime(end_at).time()
            for win in resource.schedules.filter(weekday=weekday):
                if win.start_time <= local_start and local_end <= win.end_time:
                    inside = True
                    break
            if not inside:
                raise serializers.ValidationError("Booking time is outside resource schedule")

        # Time-off collision
        if resource.timeoffs.filter(start_at__lt=end_at, end_at__gt=start_at).exists():
            raise serializers.ValidationError("Booking collides with a time-off")

        # Overlap against capacity
        overlapping = Booking.objects.filter(
            tenant=tenant,
            resource=resource,
            status__in=["booked", "confirmed"],
            start_at__lt=end_at,
            end_at__gt=start_at,
        )
        if instance:
            overlapping = overlapping.exclude(id=instance.id)

        # count bodies vs capacity
        if overlapping.count() >= resource.capacity:
            raise serializers.ValidationError("Resource capacity exceeded for this slot")

        # Price default
        if service and not data.get("price"):
            data["price"] = service.price
        if service and not data.get("currency"):
            data["currency"] = service.currency

        return data

    @transaction.atomic
    def create(self, validated_data):
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
