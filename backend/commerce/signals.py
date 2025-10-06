from decimal import Decimal
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.db import transaction
from workflow.services import emit_event
from .models import Order, OrderItem, Product, ProductImage, ProductVideo, Variant, Business

def _available(stock): return stock.qty_on_hand - stock.qty_reserved # type: ignore

def _allocate_reservations(tenant, order_item, preferred_warehouse_id=None, proportional=True, allow_backorder=False):
    from inventory.models import StockItem, StockReservation, StockLedger
    needed = order_item.qty
    variant = order_item.variant
    stocks = list(StockItem.objects.filter(tenant=tenant, variant=variant).select_related("warehouse"))
    if preferred_warehouse_id:
        stocks.sort(key=lambda s: 0 if s.warehouse_id == preferred_warehouse_id else 1)
    else:
        stocks.sort(key=lambda s: _available(s), reverse=True)
    total_avail = sum(max(0, _available(s)) for s in stocks)
    if not allow_backorder and total_avail < needed:
        raise ValueError("Insufficient stock to reserve (backorder disabled).")
    allocations = []
    remaining = needed
    if proportional and total_avail > 0:
        for s in stocks:
            avail = max(0, _available(s))
            if avail <= 0: continue
            share = int((Decimal(avail)/Decimal(total_avail))*Decimal(needed))
            take = min(avail, max(1, share)) if remaining>0 else 0
            take = min(take, remaining)
            if take>0:
                allocations.append((s,take)); remaining -= take
        i=0
        while remaining>0 and i<len(stocks):
            s=stocks[i]; avail=max(0,_available(s)); extra=min(avail,remaining)
            if extra>0: allocations.append((s,extra)); remaining-=extra
            i+=1
    else:
        for s in stocks:
            if remaining<=0: break
            avail=_available(s)
            take = remaining if allow_backorder else min(max(0,avail), remaining)
            if take>0: allocations.append((s,take)); remaining-=take
    if allow_backorder and remaining>0 and stocks:
        target = next((s for s in stocks if s.warehouse_id==preferred_warehouse_id), stocks[0])
        allocations.append((target, remaining)); remaining=0
    for stock, take in allocations:
        StockReservation.objects.create(
            tenant=tenant, order_item=order_item, variant=variant,
            warehouse=stock.warehouse, qty=take, status="reserved"
        )
        stock.qty_reserved += take
        stock.save(update_fields=["qty_reserved"])
        StockLedger.objects.create(
            tenant=tenant, variant=variant, qty_delta=0, reason="reserve",
            warehouse=stock.warehouse, order_item_id=order_item.id
        )

def _recompute_total(order):
    order.total_amount = sum((oi.qty * oi.price) for oi in order.items.all())
    order.save(update_fields=["total_amount"])

@receiver(post_save, sender=OrderItem)
def reserve_on_create(sender, instance, created, **kwargs):
    if not created: return
    from inventory.models import StockItem, StockLedger
    order = instance.order
    allow_backorder = bool(getattr(order.business, "allow_backorder", False))
    with transaction.atomic():
        _allocate_reservations(tenant=order.tenant, order_item=instance,
                               preferred_warehouse_id=None, proportional=True,
                               allow_backorder=allow_backorder)
        _recompute_total(order)

@receiver(post_delete, sender=OrderItem)
def release_on_delete(sender, instance, **kwargs):
    with transaction.atomic():
        from inventory.models import StockItem, StockLedger
        for res in instance.reservations.select_for_update():
            if res.status == "reserved":
                stock = StockItem.objects.select_for_update().get(
                    tenant=res.tenant, warehouse=res.warehouse, variant=res.variant
                )
                stock.qty_reserved = max(0, stock.qty_reserved - res.qty)
                stock.save(update_fields=["qty_reserved"])
                res.status = "released"
                res.save(update_fields=["status"])
                StockLedger.objects.create(
                    tenant=res.tenant, variant=res.variant, qty_delta=0, reason="release",
                    warehouse=res.warehouse, order_item_id=instance.id
                )
        _recompute_total(instance.order)


@receiver([post_save, post_delete], sender=Product)
@receiver([post_save, post_delete], sender=Variant)
@receiver([post_save, post_delete], sender=ProductImage)
@receiver([post_save, post_delete], sender=ProductVideo)
def invalidate_product_cache_on_change(sender, instance, **kwargs):
    product_id = instance.product_id if hasattr(instance, 'product_id') else instance.id
    # Asynchronously invalidate the cache to avoid blocking the request.
    # invalidate_product_cache_task.delay(str(product_id))

@receiver(post_save, sender=Order)
def order_created_event(sender, instance, created, **kw):
    if created:
        emit_event(tenant=instance.tenant, name="order.created", payload={"order_id": str(instance.id)})
