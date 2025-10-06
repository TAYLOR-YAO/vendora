from django.db import models
from django.utils import timezone
from common.models import BaseModel


class Resource(BaseModel):
    """
    A bookable entity: staff, room, equipment, etc.
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="resources")
    type = models.CharField(max_length=20, default="staff")  # staff|room|equip|other
    name = models.CharField(max_length=200)
    timezone = models.CharField(max_length=64, default="UTC")
    capacity = models.PositiveIntegerField(default=1)  # parallel appointments; staff typically 1
    skills = models.JSONField(default=list, blank=True)  # ["haircut","massage"]
    location = models.CharField(max_length=255, blank=True, null=True)
    color = models.CharField(max_length=16, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["tenant", "type", "is_active"])]

    def __str__(self):
        return self.name


class Service(BaseModel):
    """
    Bookable service definitions.
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, null=True)
    duration_min = models.PositiveIntegerField(default=30)
    buffer_before_min = models.PositiveIntegerField(default=0)
    buffer_after_min = models.PositiveIntegerField(default=0)
    capacity = models.PositiveIntegerField(default=1)  # how many customers per slot
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="XOF")
    is_active = models.BooleanField(default=True)
    resources = models.ManyToManyField("appointments.Resource", blank=True, related_name="services")

    class Meta:
        indexes = [models.Index(fields=["tenant", "is_active", "name"])]

    def __str__(self):
        return self.name


class ResourceSchedule(BaseModel):
    """
    Weekly recurring availability for a resource.
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="resource_schedules")
    resource = models.ForeignKey("appointments.Resource", on_delete=models.CASCADE, related_name="schedules")
    weekday = models.PositiveSmallIntegerField()  # 0=Mon … 6=Sun
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        indexes = [models.Index(fields=["tenant", "resource", "weekday"])]
        unique_together = (("resource", "weekday", "start_time", "end_time"),)


class TimeOff(BaseModel):
    """
    One-off or multi-day resource unavailability.
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="timeoffs")
    resource = models.ForeignKey("appointments.Resource", on_delete=models.CASCADE, related_name="timeoffs")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    reason = models.CharField(max_length=160, blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["tenant", "resource", "start_at", "end_at"])]


class Booking(BaseModel):
    """
    A single appointment. Supports rescheduling & cancel flow.
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="bookings")
    resource = models.ForeignKey("appointments.Resource", on_delete=models.CASCADE, related_name="bookings")
    service = models.ForeignKey("appointments.Service", on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings")

    start_at = models.DateTimeField()
    end_at = models.DateTimeField()

    status = models.CharField(max_length=20, default="booked")  # booked|confirmed|completed|cancelled|no_show
    notes = models.TextField(blank=True, null=True)

    # Reschedule / cancel audit
    reschedule_of = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="reschedules")
    cancelled_at = models.DateTimeField(blank=True, null=True)
    cancelled_by_user_id = models.UUIDField(blank=True, null=True)
    cancellation_reason = models.CharField(max_length=200, blank=True, null=True)
    source = models.CharField(max_length=20, default="web")  # web|mobile|staff|api

    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="XOF")

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "resource", "start_at", "end_at"]),
            models.Index(fields=["tenant", "status", "start_at"]),
        ]

    def __str__(self):
        return f"{self.service or 'Booking'} @ {self.start_at} – {self.resource}"
