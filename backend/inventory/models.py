from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from common.models import BaseModel

class Warehouse(BaseModel):
    tenant   = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="warehouses")
    store    = models.ForeignKey("business.Store", on_delete=models.SET_NULL, null=True, blank=True, related_name="warehouses")
    name     = models.CharField(max_length=200)
    code     = models.CharField(max_length=32, blank=True, null=True)  # short code for ops
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "is_active"]),
            models.Index(fields=["tenant", "name"]),
        ]

    def __str__(self):
        return self.name


class StockItem(BaseModel):
    tenant    = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="stock_items")
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.CASCADE, related_name="stock_items")
    variant   = models.ForeignKey("commerce.Variant", on_delete=models.CASCADE, related_name="stock_items")
    qty_on_hand = models.IntegerField(default=0)
    qty_reserved = models.IntegerField(default=0)

    class Meta:
        unique_together = (("tenant", "warehouse", "variant"),)
        indexes = [
            models.Index(fields=["tenant", "variant"]),
            models.Index(fields=["tenant", "warehouse"]),
        ]

    @property
    def qty_available(self) -> int:
        return max(0, self.qty_on_hand - self.qty_reserved)

    def clean(self):
        if self.qty_on_hand < 0:
            raise ValidationError("qty_on_hand cannot be negative")
        if self.qty_reserved < 0:
            raise ValidationError("qty_reserved cannot be negative")
        if self.qty_reserved > self.qty_on_hand:
            raise ValidationError("qty_reserved cannot exceed qty_on_hand")


class StockLedger(BaseModel):
    REASONS = (
        ("adjustment", "Adjustment"),
        ("transfer_out", "Transfer Out"),
        ("transfer_in", "Transfer In"),
        ("reserve", "Reserve"),
        ("consume", "Consume"),
        ("release", "Release"),
        ("receive", "Receive"),
        ("correction", "Correction"),
    )
    tenant    = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="stock_ledgers")
    variant   = models.ForeignKey("commerce.Variant", on_delete=models.CASCADE, related_name="stock_ledgers")
    qty_delta = models.IntegerField()
    reason    = models.CharField(max_length=32, choices=REASONS, default="adjustment")
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_ledgers")
    order_item_id = models.UUIDField(null=True, blank=True)
    note      = models.CharField(max_length=255, blank=True, null=True)
    snapshot_available = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "variant"]),
            models.Index(fields=["tenant", "warehouse"]),
            models.Index(fields=["tenant", "-created_at"]),
        ]


class StockReservation(BaseModel):
    STATUS = (
        ("reserved", "Reserved"),
        ("consumed", "Consumed"),
        ("released", "Released"),
    )
    tenant    = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="stock_reservations")
    order_item = models.ForeignKey("commerce.OrderItem", on_delete=models.CASCADE, related_name="reservations")
    variant   = models.ForeignKey("commerce.Variant", on_delete=models.CASCADE, related_name="reservations")
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.CASCADE, related_name="reservations")
    qty       = models.IntegerField()
    status    = models.CharField(max_length=16, choices=STATUS, default="reserved")

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "variant"]),
            models.Index(fields=["tenant", "warehouse"]),
            models.Index(fields=["tenant", "status"]),
        ]

    def clean(self):
        if self.qty <= 0:
            raise ValidationError("Reservation qty must be > 0")


# --- Operational models for serious inventory ops ---

class StockAdjustment(BaseModel):
    """
    Manual or system stock adjustment (e.g. cycle count).
    Positive qty_delta increases on-hand, negative decreases.
    """
    tenant    = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="stock_adjustments")
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.CASCADE, related_name="stock_adjustments")
    variant   = models.ForeignKey("commerce.Variant", on_delete=models.CASCADE, related_name="stock_adjustments")
    qty_delta = models.IntegerField()
    reason    = models.CharField(max_length=64, default="cycle_count")
    note      = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["tenant", "warehouse"]),
            models.Index(fields=["tenant", "variant"]),
        ]


class StockTransfer(BaseModel):
    """
    Move stock from one warehouse to another.
    """
    tenant     = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="stock_transfers")
    variant    = models.ForeignKey("commerce.Variant", on_delete=models.CASCADE, related_name="stock_transfers")
    source     = models.ForeignKey("inventory.Warehouse", on_delete=models.CASCADE, related_name="transfer_outs")
    destination= models.ForeignKey("inventory.Warehouse", on_delete=models.CASCADE, related_name="transfer_ins")
    qty        = models.IntegerField()
    status     = models.CharField(max_length=16, default="completed")  # draft|in_transit|completed|canceled
    note       = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["tenant", "status"]),
        ]

    def clean(self):
        if self.qty <= 0:
            raise ValidationError("Transfer qty must be > 0")
        if self.source_id == self.destination_id:
            raise ValidationError("Source and destination cannot be the same")
