from django.db import models
from django.utils import timezone
from common.models import BaseModel


class PickupCenter(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="pickup_centers")
    code = models.CharField(max_length=16)
    name = models.CharField(max_length=200)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    # NEW – optional address lines for UI maps/search
    address_line1 = models.CharField(max_length=200, blank=True, null=True)
    address_line2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=80, blank=True, null=True)
    country = models.CharField(max_length=2, default="TG", blank=True)
    phone = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["tenant", "code"]), models.Index(fields=["tenant", "city"])]
        ordering = ["name", "code"]

    def __str__(self):
        return f"{self.code} • {self.name}"


class Shipment(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="shipments")
    order = models.ForeignKey("commerce.Order", on_delete=models.CASCADE, related_name="shipments")
    address = models.ForeignKey("business.Address", on_delete=models.SET_NULL, null=True, blank=True)
    pickup_center = models.ForeignKey("shipments.PickupCenter", on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(
        max_length=20,
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("label_created", "Label Created"),
            ("in_transit", "In Transit"),
            ("partial", "Partial"),
            ("fulfilled", "Fulfilled"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
    )
    tracking = models.CharField(max_length=64, blank=True, null=True)

    # NEW – logistics
    carrier = models.CharField(max_length=40, blank=True, null=True)        # dhl|ups|local-courier|pickup
    service_level = models.CharField(max_length=40, blank=True, null=True)  # standard|express|same_day
    weight_kg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    length_cm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    width_cm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    ship_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ship_currency = models.CharField(max_length=3, default="XOF")

    label_url = models.URLField(blank=True, null=True)
    tracking_url = models.URLField(blank=True, null=True)

    shipped_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    eta = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "order"]),
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "tracking"]),
        ]
        ordering = ["-created_at"]


class ShipmentItem(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="shipment_items")
    shipment = models.ForeignKey("shipments.Shipment", on_delete=models.CASCADE, related_name="items")
    order_item = models.ForeignKey("commerce.OrderItem", on_delete=models.CASCADE, related_name="shipment_items")
    variant = models.ForeignKey("commerce.Variant", on_delete=models.CASCADE)
    qty = models.IntegerField()
    status = models.CharField(
        max_length=16,
        default="pending",
        choices=[("pending", "Pending"), ("fulfilled", "Fulfilled"), ("cancelled", "Cancelled")],
    )

    class Meta:
        indexes = [models.Index(fields=["tenant", "shipment"]), models.Index(fields=["tenant", "status"])]
