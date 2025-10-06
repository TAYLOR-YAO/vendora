from typing import Tuple
from django.db.models import Sum
from .models import StockItem, StockLedger
from commerce.models import Variant

def get_available_qty(tenant_id, variant: Variant) -> int:
    """
    Returns total qty_on_hand across all warehouses for a variant in the tenant.
    """
    agg = (
        StockItem.objects
        .filter(tenant_id=tenant_id, variant=variant)
        .aggregate(total=Sum("qty_on_hand"))
    )
    return int(agg["total"] or 0)

def allocate_stock(tenant_id, variant: Variant, qty: int) -> bool:
    """
    Deduct qty from the first warehouses that have stock (simple greedy).
    Returns True if fully allocated; False otherwise.
    """
    remaining = qty
    items = (
        StockItem.objects
        .select_for_update()
        .filter(tenant_id=tenant_id, variant=variant, qty_on_hand__gt=0)
        .order_by("-qty_on_hand")
    )
    for si in items:
        if remaining <= 0: break
        take = min(si.qty_on_hand, remaining)
        si.qty_on_hand -= take
        si.save(update_fields=["qty_on_hand"])
        StockLedger.objects.create(
            tenant_id=tenant_id, variant=variant, qty_delta=-take, reason="order_alloc"
        )
        remaining -= take
    return remaining == 0

def release_stock(tenant_id, variant: Variant, qty: int):
    """
    Return stock into the largest-depleted warehouses (simple policy).
    """
    remaining = qty
    items = (
        StockItem.objects
        .select_for_update()
        .filter(tenant_id=tenant_id, variant=variant)
        .order_by("qty_on_hand")
    )
    for si in items:
        if remaining <= 0: break
        si.qty_on_hand += remaining
        si.save(update_fields=["qty_on_hand"])
        StockLedger.objects.create(
            tenant_id=tenant_id, variant=variant, qty_delta=remaining, reason="order_release"
        )
        remaining = 0
