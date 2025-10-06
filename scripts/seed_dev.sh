#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="python"

# Ensure DB is migrated (safe to re-run)
$PYTHON_BIN backend/manage.py migrate

# Seed data (idempotent, adapts to your current schema)
$PYTHON_BIN backend/manage.py shell <<'PY'
from decimal import Decimal
from django.db import transaction
from django.contrib.auth import get_user_model
from django.apps import apps

# Core models
from platformapp.models import Tenant
from business.models import Business, Store, Address
from taxonomy.models import Industry, Category, Subcategory
from crm.models import Customer
from inventory.models import Warehouse, StockItem
from commerce.models import Product, Variant, Cart, CartItem, Order, OrderItem
from payments.models import Payment

# Optional models (may or may not exist in your tree)
ProductImage = apps.get_model('commerce', 'ProductImage', require_ready=False)
ProductVideo = apps.get_model('commerce', 'ProductVideo', require_ready=False)

# Optional notifications helper
queue_notification = None
try:
    from notificationsapp.utils import queue_notification
except Exception:
    pass

User = get_user_model()

def allowed_kwargs(model_cls, **raw):
    """
    Filter kwargs to only those fields that exist on model_cls.
    Prevents errors like 'Cannot resolve keyword "kind" into field'.
    """
    if not model_cls:
        return {}
    fields = {f.name for f in model_cls._meta.get_fields() if hasattr(f, "attname")}
    return {k: v for k, v in raw.items() if k in fields}

@transaction.atomic
def seed():
    # --- Tenant ---
    tenant, _ = Tenant.objects.get_or_create(
        slug="demo",
        defaults=dict(name="Demo Tenant", status="active", plan="free", region="africa-south1")
    )

    # --- Dev Superuser ---
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@example.com", "ChangeMe!123")

    # --- Address / Business / Store ---
    addr, _ = Address.objects.get_or_create(
        tenant=tenant, line1="123 Demo St", city="Lomé", country="TG"
    )
    biz, _ = Business.objects.get_or_create(
        tenant=tenant, url_slug="vendora-demo",
        defaults=dict(name="Vendora Demo Biz", currency="XOF", settings_json={})
    )
    store, _ = Store.objects.get_or_create(
        tenant=tenant, business=biz, name="Main Store",
        defaults=dict(type="store", url_slug="main", address=addr)
    )

    # --- Taxonomy ---
    ind, _ = Industry.objects.get_or_create(tenant=tenant, slug="apparel", defaults=dict(name="Apparel"))
    cat, _ = Category.objects.get_or_create(tenant=tenant, industry=ind, slug="tops", defaults=dict(name="Tops"))
    sub, _ = Subcategory.objects.get_or_create(tenant=tenant, category=cat, slug="tshirts", defaults=dict(name="T-Shirts"))

    # --- Product & Variants ---
    tee, _ = Product.objects.get_or_create(
        tenant=tenant, business=biz, name="Classic Tee",
        defaults=dict(type="physical", default_price=Decimal("15.00"), currency="XOF", is_active=True)
    )

    # Attach media only with fields your models actually have
    if ProductImage:
        pi_kwargs = allowed_kwargs(ProductImage,
            tenant=tenant, product=tee, url="https://example.com/tee-front.jpg",
            alt_text="Front", position=1, kind="image"     # 'kind' will be dropped if not present
        )
        ProductImage.objects.get_or_create(**pi_kwargs)

        pi_kwargs = allowed_kwargs(ProductImage,
            tenant=tenant, product=tee, url="https://example.com/tee-back.jpg",
            alt_text="Back", position=2, kind="image"
        )
        ProductImage.objects.get_or_create(**pi_kwargs)

    if ProductVideo:
        pv_kwargs = allowed_kwargs(ProductVideo,
            tenant=tenant, product=tee, url="https://example.com/tee-demo.mp4",
            position=1, kind="video"                       # dropped if not present
        )
        ProductVideo.objects.get_or_create(**pv_kwargs)

    v_s, _ = Variant.objects.get_or_create(
        tenant=tenant, product=tee, sku="TEE-S", defaults=dict(price=Decimal("15.00"), is_active=True)
    )
    v_m, _ = Variant.objects.get_or_create(
        tenant=tenant, product=tee, sku="TEE-M", defaults=dict(price=Decimal("15.00"), is_active=True)
    )
    v_l, _ = Variant.objects.get_or_create(
        tenant=tenant, product=tee, sku="TEE-L", defaults=dict(price=Decimal("15.00"), is_active=True)
    )

    # --- Warehouse + Initial Stock (so first order works) ---
    wh, _ = Warehouse.objects.get_or_create(
        tenant=tenant, store=store, name="Main Warehouse"
    )

    def ensure_qty(variant, min_qty):
        si, _ = StockItem.objects.get_or_create(
            tenant=tenant, warehouse=wh, variant=variant, defaults=dict(qty_on_hand=min_qty)
        )
        if si.qty_on_hand < min_qty:
            si.qty_on_hand = min_qty
            si.save(update_fields=["qty_on_hand"])

    for v in (v_s, v_m, v_l):
        ensure_qty(v, 50)

    # --- Customer ---
    cust, _ = Customer.objects.get_or_create(
        tenant=tenant, name="John Doe",
        defaults=dict(type="person", email="john@example.com", phone="+22800000000")
    )

    # --- Cart -> Order ---
    cart, _ = Cart.objects.get_or_create(tenant=tenant, customer=cust, status="open")
    CartItem.objects.filter(tenant=tenant, cart=cart).delete()
    CartItem.objects.create(tenant=tenant, cart=cart, variant=v_m, qty=2, price=Decimal("15.00"))
    CartItem.objects.create(tenant=tenant, cart=cart, variant=v_l, qty=1, price=Decimal("15.00"))

    order, _ = Order.objects.get_or_create(
        tenant=tenant, business=biz, customer=cust, status="pending", currency="XOF",
        defaults=dict(total_amount=Decimal("0.00"))
    )
    OrderItem.objects.filter(tenant=tenant, order=order).delete()

    total = Decimal("0.00")
    for ci in CartItem.objects.filter(tenant=tenant, cart=cart):
        OrderItem.objects.create(
            tenant=tenant, order=order, variant=ci.variant, qty=ci.qty, price=ci.price
        )
        total += (ci.price * ci.qty)

    if order.total_amount != total:
        order.total_amount = total
        order.save(update_fields=["total_amount"])

    if cart.status != "closed":
        cart.status = "closed"
        cart.save(update_fields=["status"])

    # --- Payment: mark succeeded (will flip order to 'paid' if your signal exists) ---
    pay, created = Payment.objects.get_or_create(
        tenant=tenant, order=order,
        defaults=dict(amount=order.total_amount, currency=order.currency,
                      status="succeeded", provider="card", provider_ref="SEED-TXN-001")
    )
    if not created and pay.status != "succeeded":
        pay.status = "succeeded"
        pay.save(update_fields=["status"])

    # If you don't have the payment→order 'paid' signal yet, force it:
    if order.status != "paid":
        order.status = "paid"
        order.save(update_fields=["status"])

    # Optional notification
    if queue_notification:
        try:
            queue_notification(
                tenant=tenant, template=None, to_address="john@example.com", channel="email",
                payload={"subject":"Order paid","message":f"Order {order.id} paid: {order.total_amount} {order.currency}"}
            )
        except Exception:
            pass

    print("Seed complete.")
    print(f"Tenant: {tenant.id}  Business: {biz.id}  Store: {store.id}  Warehouse: {wh.id}")
    print(f"Product: {tee.id}  Variants: {[v_s.sku, v_m.sku, v_l.sku]}  Customer: {cust.id}")
    print(f"Order: {order.id}  Total: {order.total_amount} {order.currency}  Status: {order.status}")
    print("Initial stock set to >= 50 units for each variant in Main Warehouse.")

seed()
PY

echo "OK — seed completed."
echo "Try API:"
echo "  /api/v1/core/healthz/"
echo "  /api/v1/commerce/product/"
echo "  /api/v1/commerce/variant/?tenant=<TENANT_UUID>"
echo "  /api/v1/inventory/stockitem/?tenant=<TENANT_UUID>"
echo "  /api/v1/commerce/order/?tenant=<TENANT_UUID>"
