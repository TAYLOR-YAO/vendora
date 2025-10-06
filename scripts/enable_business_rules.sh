#!/usr/bin/env bash
set -euo pipefail

# Helper to write files safely
write() { mkdir -p "$(dirname "$1")"; cat > "$1" <<'EOF'
$CONTENT
EOF
}

# ------------------------------
# commerce/serializers.py (nested)
# ------------------------------
CONTENT='
from decimal import Decimal
from typing import List, Optional

from django.apps import apps
from django.db import transaction
from rest_framework import serializers

from .models import Product, Variant  # ProductImage/ProductVideo may or may not exist

# Try to import optional media models; fall back to None
try:
    from .models import ProductImage
except Exception:
    ProductImage = None

try:
    from .models import ProductVideo
except Exception:
    ProductVideo = None


class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = "__all__"


# If media models do not exist, provide minimal placeholders so nested input is accepted & ignored.
if ProductImage:
    class ProductImageSerializer(serializers.ModelSerializer):
        class Meta:
            model = ProductImage
            fields = "__all__"
else:
    class ProductImageSerializer(serializers.Serializer):
        url = serializers.URLField()
        alt_text = serializers.CharField(required=False, allow_blank=True)
        position = serializers.IntegerField(required=False)
        def create(self, validated): return validated
        def update(self, instance, validated): return instance

if ProductVideo:
    class ProductVideoSerializer(serializers.ModelSerializer):
        class Meta:
            model = ProductVideo
            fields = "__all__"
else:
    class ProductVideoSerializer(serializers.Serializer):
        url = serializers.URLField()
        position = serializers.IntegerField(required=False)
        def create(self, validated): return validated
        def update(self, instance, validated): return instance


class ProductSerializer(serializers.ModelSerializer):
    """
    Writable nested serializer:
    - Accepts lists: images, videos, variants
    - Tenancy: pass tenant via request.data or include it in nested items; we will set it when missing
    """
    images = ProductImageSerializer(many=True, required=False)
    videos = ProductVideoSerializer(many=True, required=False)
    variants = VariantSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = "__all__"

    def _tenant_id(self):
        # prefer explicit field on product payload, otherwise request.query_params (auto API uses ?tenant=<uuid>)
        tid = self.initial_data.get("tenant") if isinstance(self.initial_data, dict) else None
        if not tid:
            req = self.context.get("request")
            if req:
                tid = req.data.get("tenant") or req.query_params.get("tenant")
        return tid

    @transaction.atomic
    def create(self, validated_data):
        img_data = validated_data.pop("images", [])
        vid_data = validated_data.pop("videos", [])
        var_data = validated_data.pop("variants", [])

        product = super().create(validated_data)
        tenant_id = product.tenant_id or self._tenant_id()

        # Create variants
        for v in var_data or []:
            v.setdefault("tenant", tenant_id)
            v["product"] = product.id
            Variant.objects.create(**v)

        # Media are optional; only create if models exist
        if ProductImage:
            for i in img_data or []:
                i.setdefault("tenant", tenant_id)
                i["product"] = product.id
                ProductImage.objects.create(**i)

        if ProductVideo:
            for v in vid_data or []:
                v.setdefault("tenant", tenant_id)
                v["product"] = product.id
                ProductVideo.objects.create(**v)

        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        img_data = validated_data.pop("images", None)
        vid_data = validated_data.pop("videos", None)
        var_data = validated_data.pop("variants", None)

        product = super().update(instance, validated_data)
        tenant_id = product.tenant_id or self._tenant_id()

        def _sync_children(model_cls, current_qs, incoming_list, fk_name="product"):
            # Simple replace strategy: delete + recreate
            current_qs.all().delete()
            for payload in incoming_list or []:
                payload.setdefault("tenant", tenant_id)
                payload[fk_name] = product.id
                model_cls.objects.create(**payload)

        # Variants
        if var_data is not None:
            _sync_children(Variant, Variant.objects.filter(product=product), var_data)

        # Media
        if ProductImage and img_data is not None:
            _sync_children(ProductImage, ProductImage.objects.filter(product=product), img_data)
        if ProductVideo and vid_data is not None:
            _sync_children(ProductVideo, ProductVideo.objects.filter(product=product), vid_data)

        return product
'
write backend/commerce/serializers.py

# ------------------------------
# commerce/signals.py
# ------------------------------
CONTENT='
from decimal import Decimal
from django.db import transaction
from django.db.models.signals import pre_save, post_delete, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError

from commerce.models import OrderItem, Order
from inventory.models import StockItem, StockLedger
from payments.models import Payment

def _order_total(order: Order):
    agg = order.items.all().values_list("qty","price")
    return sum((q * p for q,p in agg), Decimal("0.00"))

def _adjust_stock(tenant_id, variant_id, qty_delta: int, reason: str):
    """
    qty_delta: positive increases on-hand (restock), negative consumes stock.
    Enforces no-negative via SELECT ... FOR UPDATE.
    Creates a StockLedger record.
    """
    with transaction.atomic():
        # lock a single StockItem row – choose any warehouse holding it;
        # if multiple warehouses exist, a more complex allocation policy can be added.
        si = (StockItem.objects
              .select_for_update()
              .filter(tenant_id=tenant_id, variant_id=variant_id)
              .order_by("id")
              .first())
        if not si:
            raise ValidationError("No stock found for variant.")
        new_qty = si.qty_on_hand + qty_delta
        if new_qty < 0:
            raise ValidationError("Insufficient stock.")
        si.qty_on_hand = new_qty
        si.save(update_fields=["qty_on_hand"])
        StockLedger.objects.create(
            tenant_id=tenant_id, variant_id=variant_id,
            qty_delta=qty_delta, reason=reason
        )

@receiver(pre_save, sender=OrderItem)
def oi_pre_save_stock_enforce(sender, instance: OrderItem, **kwargs):
    """
    On OrderItem create/update:
    - compute delta = new_qty - old_qty (0 if create)
    - reduce stock by delta (negative delta means restore stock)
    - block if result would be negative
    """
    if not instance.pk:
        old_qty = 0
    else:
        old_qty = sender.objects.filter(pk=instance.pk).values_list("qty", flat=True).first() or 0
    delta = instance.qty - old_qty
    if delta != 0:
        # consume stock: negative delta to _adjust_stock means restock; positive means consume
        _adjust_stock(instance.tenant_id, instance.variant_id, qty_delta=-delta, reason="order_item")

@receiver(post_delete, sender=OrderItem)
def oi_post_delete_restock(sender, instance: OrderItem, **kwargs):
    # Undo the reserved stock if an item is removed
    if instance.qty:
        _adjust_stock(instance.tenant_id, instance.variant_id, qty_delta=instance.qty, reason="order_item_delete")

@receiver(post_save, sender=OrderItem)
def oi_post_save_recompute(sender, instance: OrderItem, **kwargs):
    # recompute order total on any change
    order = instance.order
    total = _order_total(order)
    if total != order.total_amount:
        order.total_amount = total
        order.save(update_fields=["total_amount"])

@receiver(post_save, sender=Payment)
def payment_post_save_mark_paid(sender, instance: Payment, created, **kwargs):
    """
    When a payment becomes `succeeded`:
     - mark order as paid (idempotent)
     - optionally enqueue notification
    """
    if instance.status != "succeeded":
        return
    order = instance.order
    if order.status != "paid":
        order.status = "paid"
        order.save(update_fields=["status"])
        # Optional notification
        try:
            from notificationsapp.utils import queue_notification
            queue_notification(
                tenant=order.tenant, template=None, to_address=getattr(order.customer, "email", None),
                channel="email",
                payload={"subject": "Order paid",
                         "message": f"Order {order.id} paid: {order.total_amount} {order.currency}"}
            )
        except Exception:
            # notifications are best-effort in dev
            pass
'
write backend/commerce/signals.py

# ------------------------------
# inventory/signals.py (optional extras for future behaviors)
# ------------------------------
CONTENT='
# Currently stock changes are handled in commerce/signals via _adjust_stock.
# Keep this file as an extension point for future inventory-specific automation.
'
write backend/inventory/signals.py

# ------------------------------
# apps.py: ensure signals import on ready()
# ------------------------------
# We will replace the apps.py in three apps to import signals.

CONTENT='
from django.apps import AppConfig
class CommerceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "commerce"
    def ready(self):
        from . import signals  # noqa: F401
'
write backend/commerce/apps.py

CONTENT='
from django.apps import AppConfig
class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"
    def ready(self):
        from . import signals  # noqa: F401
'
write backend/inventory/apps.py

CONTENT='
from django.apps import AppConfig
class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "payments"
    def ready(self):
        # payment→order paid signal is defined in commerce.signals (hooked via CommerceConfig)
        # Keeping this for symmetry/extension if you later move payment signals here.
        try:
            from commerce import signals  # noqa: F401
        except Exception:
            pass
'
write backend/payments/apps.py

echo "✓ Files written. Now run:"
echo "  python backend/manage.py makemigrations  # (should be no model changes)"
echo "  python backend/manage.py migrate"
echo "  python backend/manage.py runserver 0.0.0.0:8080"
