from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

from .models import Invoice


def _generate_number(tenant_id: str) -> str:
    # Super simple prefix by year; swap with a per-tenant sequence later.
    y = timezone.now().strftime("%Y")
    from uuid import uuid4
    return f"INV-{y}-{str(uuid4())[:8].upper()}"


@receiver(pre_save, sender=Invoice)
def fill_invoice_defaults(sender, instance: Invoice, **kwargs):
    # Number
    if not instance.number:
        instance.number = _generate_number(str(instance.tenant_id))

    # Snapshot amounts from order if not provided
    if instance.total_amount == 0 and instance.order_id:
        order = instance.order
        # if your Order already maintains a total_amount/currency, use that:
        instance.currency = order.currency
        if hasattr(order, "total_amount"):
            instance.subtotal_amount = order.total_amount  # or compute from items
            # tax/discount could be computed based on your rules; keep zero if none
            instance.total_amount = (instance.subtotal_amount or Decimal("0")) \
                                    + (instance.tax_amount or Decimal("0")) \
                                    - (instance.discount_amount or Decimal("0"))
