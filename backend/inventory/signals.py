from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import StockAdjustment, StockTransfer, StockItem, StockLedger


@receiver(post_save, sender=StockAdjustment)
def apply_stock_adjustment(sender, instance: StockAdjustment, created, **kwargs):
    if not created:
        return
    with transaction.atomic():
        item, _ = StockItem.objects.select_for_update().get_or_create(
            tenant=instance.tenant, warehouse=instance.warehouse, variant=instance.variant,
            defaults={"qty_on_hand": 0, "qty_reserved": 0},
        )
        item.qty_on_hand = max(0, item.qty_on_hand + instance.qty_delta)
        item.full_clean()
        item.save(update_fields=["qty_on_hand", "updated_at"])

        StockLedger.objects.create(
            tenant=instance.tenant,
            variant=instance.variant,
            warehouse=instance.warehouse,
            qty_delta=instance.qty_delta,
            reason="adjustment",
            note=instance.reason,
            snapshot_available=item.qty_on_hand - item.qty_reserved,
        )


@receiver(post_save, sender=StockTransfer)
def apply_stock_transfer(sender, instance: StockTransfer, created, **kwargs):
    if not created:
        return
    if instance.status != "completed":
        return
    with transaction.atomic():
        # OUT
        out_item, _ = StockItem.objects.select_for_update().get_or_create(
            tenant=instance.tenant, warehouse=instance.source, variant=instance.variant,
            defaults={"qty_on_hand": 0, "qty_reserved": 0},
        )
        if out_item.qty_on_hand - out_item.qty_reserved < instance.qty:
            # not enough available; you may decide to raise or allow negative
            raise ValueError("Insufficient available stock to transfer")

        out_item.qty_on_hand -= instance.qty
        out_item.full_clean()
        out_item.save(update_fields=["qty_on_hand", "updated_at"])
        StockLedger.objects.create(
            tenant=instance.tenant, variant=instance.variant, warehouse=instance.source,
            qty_delta=-instance.qty, reason="transfer_out",
            snapshot_available=out_item.qty_on_hand - out_item.qty_reserved,
            note=instance.note,
        )

        # IN
        in_item, _ = StockItem.objects.select_for_update().get_or_create(
            tenant=instance.tenant, warehouse=instance.destination, variant=instance.variant,
            defaults={"qty_on_hand": 0, "qty_reserved": 0},
        )
        in_item.qty_on_hand += instance.qty
        in_item.full_clean()
        in_item.save(update_fields=["qty_on_hand", "updated_at"])
        StockLedger.objects.create(
            tenant=instance.tenant, variant=instance.variant, warehouse=instance.destination,
            qty_delta=instance.qty, reason="transfer_in",
            snapshot_available=in_item.qty_on_hand - in_item.qty_reserved,
            note=instance.note,
        )
