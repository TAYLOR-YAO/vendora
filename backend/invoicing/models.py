from django.db import models
from django.utils import timezone
from common.models import BaseModel


class TaxRate(BaseModel):
    """
    Public-readable (for catalog/checkout), tenant-owned for management.
    """
    tenant = models.ForeignKey(
        "platformapp.Tenant", on_delete=models.CASCADE, related_name="tax_rates"
    )
    country = models.CharField(max_length=2, default="TG")
    name = models.CharField(max_length=80)
    rate = models.DecimalField(max_digits=6, decimal_places=4)  # e.g. 0.1800 for 18%

    class Meta:
        unique_together = ("tenant", "country", "name")
        indexes = [
            models.Index(fields=["tenant", "country", "name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.country})"


class Invoice(BaseModel):
    """
    Private by default (list/retrieve require auth), tenant-scoped.
    Keeps linkage to order but stores monetary snapshots to avoid drift.
    """
    tenant = models.ForeignKey(
        "platformapp.Tenant", on_delete=models.CASCADE, related_name="invoices"
    )
    order = models.ForeignKey(
        "commerce.Order", on_delete=models.CASCADE, related_name="invoices"
    )

    # Human-friendly number (auto-filled in signal if not provided)
    number = models.CharField(max_length=50)

    # Monetary snapshot (so invoice remains immutable even if order changes)
    subtotal_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="XOF")

    # Lifecycle/status + important dates
    status = models.CharField(
        max_length=20,
        default="open",
        choices=[
            ("open", "Open"),
            ("sent", "Sent"),
            ("paid", "Paid"),
            ("void", "Void"),
            ("overdue", "Overdue"),
        ],
    )
    issued_at = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    # Optional presentation
    pdf_url = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    billing_name = models.CharField(max_length=200, blank=True, null=True)
    billing_email = models.EmailField(blank=True, null=True)

    class Meta:
        unique_together = ("tenant", "number")
        indexes = [
            models.Index(fields=["tenant", "number"]),
            models.Index(fields=["tenant", "status", "issued_at"]),
        ]

    def __str__(self):
        return self.number
