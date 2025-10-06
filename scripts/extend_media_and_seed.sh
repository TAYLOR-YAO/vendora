#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import textwrap, pathlib

root = pathlib.Path(".")

def W(path, content):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    print("wrote", path)

# ---------- backend/commerce/serializers.py (writable nested) ----------
W("backend/commerce/serializers.py", """
from decimal import Decimal
from typing import Optional
from django.db import transaction
from rest_framework import serializers
from .models import Product, Variant

# Optional media models (present if you added them)
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


if ProductVideo:
    class ProductVideoSerializer(serializers.ModelSerializer):
        class Meta:
            model = ProductVideo
            fields = "__all__"
else:
    class ProductVideoSerializer(serializers.Serializer):
        url = serializers.URLField()
        position = serializers.IntegerField(required=False)


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, required=False)
    videos = ProductVideoSerializer(many=True, required=False)
    variants = VariantSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = "__all__"

    def _tenant_id(self) -> Optional[str]:
        data = self.initial_data if isinstance(self.initial_data, dict) else {}
        tid = data.get("tenant")
        if not tid:
            req = self.context.get("request")
            if req:
                tid = req.data.get("tenant") or req.query_params.get("tenant")
        return tid

    @transaction.atomic
    def create(self, validated):
        imgs = validated.pop("images", [])
        vids = validated.pop("videos", [])
        vars = validated.pop("variants", [])

        obj = super().create(validated)
        tenant_id = obj.tenant_id or self._tenant_id()

        for v in vars or []:
            v.setdefault("tenant", tenant_id)
            v["product"] = obj.id
            Variant.objects.create(**v)

        if ProductImage:
            for i in imgs or []:
                i.setdefault("tenant", tenant_id)
                i["product"] = obj.id
                ProductImage.objects.create(**i)
        if ProductVideo:
            for v in vids or []:
                v.setdefault("tenant", tenant_id)
                v["product"] = obj.id
                ProductVideo.objects.create(**v)

        return obj

    @transaction.atomic
    def update(self, instance, validated):
        imgs = validated.pop("images", None)
        vids = validated.pop("videos", None)
        vars = validated.pop("variants", None)
        obj = super().update(instance, validated)
        tenant_id = obj.tenant_id or self._tenant_id()

        def replace_children(model_cls, qs, incoming, fk="product"):
            qs.all().delete()
            for payload in incoming or []:
                payload.setdefault("tenant", tenant_id)
                payload[fk] = obj.id
                model_cls.objects.create(**payload)

        if vars is not None:
            from .models import Variant
            replace_children(Variant, Variant.objects.filter(product=obj), vars)

        if ProductImage and imgs is not None:
            replace_children(ProductImage, ProductImage.objects.filter(product=obj), imgs)
        if ProductVideo and vids is not None:
            replace_children(ProductVideo, ProductVideo.objects.filter(product=obj), vids)

        return obj
""")

# ---------- backend/commerce/signals.py ----------
W("backend/commerce/signals.py", """
from decimal import Decimal
from django.db import transaction
from django.db.models.signals import pre_save, post_delete, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from commerce.models import OrderItem, Order
from inventory.models import StockItem, StockLedger
from payments.models import Payment

def _order_total(order: Order) -> Decimal:
    total = Decimal("0.00")
    for qty, price in order.items.all().values_list("qty", "price"):
        total += (qty * price)
    return total

def _adjust_stock(tenant_id, variant_id, qty_delta: int, reason: str):
    with transaction.atomic():
        si = (StockItem.objects
              .select_for_update()
              .filter(tenant_id=tenant_id, variant_id=variant_id)
              .order_by("id").first())
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
def oi_pre_save_stock(sender, instance: OrderItem, **kwargs):
    old_qty = 0
    if instance.pk:
        old_qty = sender.objects.filter(pk=instance.pk).values_list("qty", flat=True).first() or 0
    delta = instance.qty - old_qty
    if delta != 0:
        _adjust_stock(instance.tenant_id, instance.variant_id, qty_delta=-delta, reason="order_item")

@receiver(post_delete, sender=OrderItem)
def oi_post_delete_restock(sender, instance: OrderItem, **kwargs):
    if instance.qty:
        _adjust_stock(instance.tenant_id, instance.variant_id, qty_delta=instance.qty, reason="order_item_delete")

@receiver(post_save, sender=OrderItem)
def oi_post_save_total(sender, instance: OrderItem, **kwargs):
    order = instance.order
    total = _order_total(order)
    if total != order.total_amount:
        order.total_amount = total
        order.save(update_fields=["total_amount"])

@receiver(post_save, sender=Payment)
def payment_paid(sender, instance: Payment, created, **kwargs):
    if instance.status != "succeeded":
        return
    order = instance.order
    if order.status != "paid":
        order.status = "paid"
        order.save(update_fields=["status"])
        try:
            from notificationsapp.utils import queue_notification
            queue_notification(
                tenant=order.tenant,
                to_address=getattr(order.customer, "email", None),
                channel="email",
                payload={"subject": "Order paid",
                         "message": f"Order {order.id} paid: {order.total_amount} {order.currency}"}
            )
        except Exception:
            pass
""")

# ---------- inventory/signals.py (extension point) ----------
W("backend/inventory/signals.py", """
# Stock adjustments are driven from commerce.signals via _adjust_stock.
# Keep this module for future inventory-specific automation.
""")

# ---------- apps.py loaders (ready() imports) ----------
W("backend/commerce/apps.py", """
from django.apps import AppConfig
class CommerceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "commerce"
    def ready(self):
        from . import signals  # noqa: F401
""")

W("backend/inventory/apps.py", """
from django.apps import AppConfig
class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"
    def ready(self):
        from . import signals  # noqa: F401
""")

W("backend/payments/apps.py", """
from django.apps import AppConfig
class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "payments"
    def ready(self):
        # Payment success handler lives in commerce.signals.
        try:
            from commerce import signals  # noqa: F401
        except Exception:
            pass
""")

print("OK - business rules files written.")
PY

echo ""
echo "Next:"
echo "1) Ensure INSTALLED_APPS uses app configs:"
echo "   'commerce.apps.CommerceConfig', 'inventory.apps.InventoryConfig', 'payments.apps.PaymentsConfig'"
echo "2) python backend/manage.py makemigrations"
echo "3) python backend/manage.py migrate"
echo "4) python backend/manage.py runserver 0.0.0.0:8080"
