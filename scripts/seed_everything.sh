#!/usr/bin/env bash
set -euo pipefail

PYBIN="${PYBIN:-python}"
MANAGE="backend/manage.py"

echo "==> Migrating (to ensure all tables exist)..."
$PYBIN "$MANAGE" migrate --noinput

echo "==> Seeding data..."
$PYBIN "$MANAGE" shell <<'PY'
import uuid
from decimal import Decimal
from django.utils import timezone
from django.apps import apps
from django.db import transaction
from django.contrib.auth import get_user_model

def M(label): return apps.get_model(label)
def flex_fields(model):
    return {f.name for f in model._meta.get_fields()
            if getattr(f, "concrete", True) and not getattr(f, "many_to_many", False)}

def create_or_first(label, **kwargs):
    m = M(label)
    fields = flex_fields(m)
    data = {k:v for k,v in kwargs.items() if k in fields}
    keys = [k for k in ("slug","email","sku","code","number","key","template_key","name") if k in data]
    q = {k:data[k] for k in keys}
    if q:
        obj = m.objects.filter(**q).first()
        if obj: return obj
    obj = m.objects.filter(**data).first()
    return obj or m.objects.create(**data)

@transaction.atomic
def seed():
    now = timezone.now()
    # ---------- Platform & Auth ----------
    Tenant = M("platformapp.Tenant"); Role = M("platformapp.Role")
    UserRole = M("platformapp.UserRole"); AuditLog = M("platformapp.AuditLog")
    User = get_user_model()

    tenant = create_or_first("platformapp.Tenant", slug="acme", name="ACME Corp", plan="pro", region="us")
    role_owner = create_or_first("platformapp.Role", tenant=tenant, name="owner", scope_level="business")
    user = User.objects.filter(email="admin@acme.test").first()
    if not user:
        user = User.objects.create_superuser(email="admin@acme.test", password="Admin123!", full_name="ACME Admin")
    create_or_first("platformapp.UserRole", tenant=tenant, role=role_owner, user_id=user.id)

    # Sites / Allauth / Token
    Site = M("sites.Site")
    site = create_or_first("sites.Site", domain="localhost:8080", name="Local Dev")
    EmailAddress = M("account.EmailAddress")
    create_or_first("account.EmailAddress", user=user, email=user.email, verified=True, primary=True)
    SocialApp = M("socialaccount.SocialApp")
    social_app = create_or_first("socialaccount.SocialApp", provider="google", name="Google OAuth (dev)",
                                 client_id="GOOGLE_CLIENT_ID", secret="GOOGLE_CLIENT_SECRET")
    if hasattr(social_app, "sites") and site not in social_app.sites.all():
        social_app.sites.add(site)
    SocialAccount = M("socialaccount.SocialAccount")
    sa = create_or_first("socialaccount.SocialAccount", user=user, provider="google", uid="google-oauth2|demo-uid")
    SocialToken = M("socialaccount.SocialToken")
    create_or_first("socialaccount.SocialToken", app=social_app, account=sa, token="dev-social-token")
    Token = M("authtoken.Token")
    Token.objects.get_or_create(user=user)

    # ---------- Taxonomy ----------
    ind = create_or_first("taxonomy.Industry", tenant=tenant, name="Retail", slug="retail")
    cat = create_or_first("taxonomy.Category", tenant=tenant, industry=ind, name="Electronics", slug="electronics")
    sub = create_or_first("taxonomy.Subcategory", tenant=tenant, category=cat, name="Phones", slug="phones")

    # ---------- Business / Stores / HR ----------
    addr = create_or_first("business.Address", tenant=tenant, line1="100 Main St", city="Metropolis", country="US")
    biz = create_or_first("business.Business", tenant=tenant, name="ACME Stores", url_slug="acme", currency="USD")
    store1 = create_or_first("business.Store", tenant=tenant, business=biz, name="ACME HQ", type="office", url_slug="hq", address=addr)
    store2 = create_or_first("business.Store", tenant=tenant, business=biz, name="ACME Downtown", type="retail", url_slug="downtown", address=addr)
    create_or_first("hr.Employee", tenant=tenant, business=biz, store=store1, first_name="Jane", last_name="Manager",
                    email="jane.manager@acme.test", status="active")

    # ---------- CRM ----------
    cust = create_or_first("crm.Customer", tenant=tenant, type="person", name="John Doe", email="john@doe.test", phone="123456789")
    create_or_first("crm.Contact", tenant=tenant, customer=cust, first_name="John", last_name="Doe",
                    email="john@doe.test", phone="123456789")
    pipe = create_or_first("crm.Pipeline", tenant=tenant, name="Default Sales")
    create_or_first("crm.Opportunity", tenant=tenant, pipeline=pipe, name="Phone order", amount=0, stage="new")
    create_or_first("crm.Activity", tenant=tenant, customer=cust, kind="note", content="Customer called about phones.")

    # ---------- Commerce ----------
    Product = M("commerce.Product"); Variant = M("commerce.Variant")
    ProductImage = M("commerce.ProductImage"); ProductVideo = M("commerce.ProductVideo")
    Cart = M("commerce.Cart"); CartItem = M("commerce.CartItem")
    Order = M("commerce.Order"); OrderItem = M("commerce.OrderItem"); Review = M("commerce.Review")

    prod = create_or_first("commerce.Product", tenant=tenant, business=biz, name="Smartphone X",
                           type="physical", default_price=Decimal("499.00"), currency="USD", is_active=True)
    create_or_first("commerce.ProductImage", tenant=tenant, product=prod, url="https://pics.example/x-front.jpg", alt_text="Front", position=1)
    create_or_first("commerce.ProductImage", tenant=tenant, product=prod, url="https://pics.example/x-back.jpg", alt_text="Back", position=2)
    create_or_first("commerce.ProductVideo", tenant=tenant, product=prod, url="https://video.example/x-demo.mp4", title="Demo")

    v1 = create_or_first("commerce.Variant", tenant=tenant, product=prod, sku="X-BLK-64", price=Decimal("499.00"), is_active=True)
    v2 = create_or_first("commerce.Variant", tenant=tenant, product=prod, sku="X-BLK-128", price=Decimal("549.00"), is_active=True)

    cart = create_or_first("commerce.Cart", tenant=tenant, customer=cust, status="open")
    create_or_first("commerce.CartItem", tenant=tenant, cart=cart, variant=v1, qty=2, price=Decimal("499.00"))

    order = create_or_first("commerce.Order", tenant=tenant, business=biz, customer=cust,
                            status="pending", total_amount=Decimal("0.00"), currency="USD")
    oi1 = create_or_first("commerce.OrderItem", tenant=tenant, order=order, variant=v1, qty=1, price=Decimal("499.00"))
    oi2 = create_or_first("commerce.OrderItem", tenant=tenant, order=order, variant=v2, qty=1, price=Decimal("549.00"))
    create_or_first("commerce.Review", tenant=tenant, product=prod, rating=5, comment="Great phone!")

    # recompute order total if no signal yet
    try:
        total = sum(Decimal(str(i.price)) * i.qty for i in OrderItem.objects.filter(order=order))
        if total and order.total_amount != total:
            order.total_amount = total
            order.save(update_fields=["total_amount"])
    except Exception:
        pass

    # ---------- Inventory ----------
    Warehouse = M("inventory.Warehouse"); StockItem = M("inventory.StockItem")
    StockLedger = M("inventory.StockLedger"); StockReservation = M("inventory.StockReservation")

    wh1 = create_or_first("inventory.Warehouse", tenant=tenant, store=store1, name="HQ Warehouse")
    wh2 = create_or_first("inventory.Warehouse", tenant=tenant, store=store2, name="Downtown Warehouse")

    si_v1 = create_or_first("inventory.StockItem", tenant=tenant, warehouse=wh1, variant=v1, qty_on_hand=100)
    si_v2 = create_or_first("inventory.StockItem", tenant=tenant, warehouse=wh1, variant=v2, qty_on_hand=80)
    create_or_first("inventory.StockLedger", tenant=tenant, variant=v1, warehouse=wh1, qty_delta=100, reason="seed")
    create_or_first("inventory.StockLedger", tenant=tenant, variant=v2, warehouse=wh1, qty_delta=80, reason="seed")

    # ✅ FIX: reservations must reference order_item (NOT NULL)
    # make them idempotent by filtering on order_item specifically
    StockReservation.objects.get_or_create(
        tenant=tenant, warehouse=wh1, variant=v1, order_item=oi1,
        defaults={"qty": oi1.qty}
    )
    StockReservation.objects.get_or_create(
        tenant=tenant, warehouse=wh1, variant=v2, order_item=oi2,
        defaults={"qty": oi2.qty}
    )

    # ---------- Payments / Invoicing ----------
    GatewayAccount = M("payments.GatewayAccount"); Payment = M("payments.Payment")
    Refund = M("payments.Refund"); Payout = M("payments.Payout")
    ga = create_or_first("payments.GatewayAccount", tenant=tenant, kind="card",
                         config={"provider":"stripe","mode":"test"})
    pay = create_or_first("payments.Payment", tenant=tenant, order=order,
                          amount=order.total_amount or Decimal("1048.00"),
                          currency="USD", status="succeeded", provider="card", provider_ref="pm_dev_123")

    TaxRate = M("invoicing.TaxRate"); Invoice = M("invoicing.Invoice")
    tax = create_or_first("invoicing.TaxRate", tenant=tenant, country="US", name="Sales Tax", rate=Decimal("0.0700"))
    inv = create_or_first("invoicing.Invoice", tenant=tenant, order=order, number="INV-0001",
                          total_amount=(order.total_amount or Decimal("1048.00")) * Decimal("1.07"),
                          currency="USD", status="open")

    # ---------- Shipments ----------
    PickupCenter = M("shipments.PickupCenter"); Shipment = M("shipments.Shipment"); ShipmentItem = M("shipments.ShipmentItem")
    pc = create_or_first("shipments.PickupCenter", tenant=tenant, code="PC001", name="ACME Pickup Center", lat=0.0, lng=0.0)
    shp = create_or_first("shipments.Shipment", tenant=tenant, order=order, pickup_center=pc, status="ready", tracking="TRK123456")
    # adapt to model shape
    kwargs = {"tenant":tenant, "shipment":shp, "qty":1}
    if "order" in flex_fields(ShipmentItem): kwargs["order"] = order
    if "order_item" in flex_fields(ShipmentItem): kwargs["order_item"] = oi1
    if "variant" in flex_fields(ShipmentItem): kwargs["variant"] = oi1.variant
    create_or_first("shipments.ShipmentItem", **kwargs)

    # ---------- Notifications ----------
    NotificationTemplate = M("notificationsapp.NotificationTemplate")
    NotificationPreference = M("notificationsapp.NotificationPreference")
    NotificationDispatch = M("notificationsapp.NotificationDispatch")
    NotificationLog = M("notificationsapp.NotificationLog")

    tmpl = create_or_first("notificationsapp.NotificationTemplate", tenant=tenant, template_key="payment_succeeded",
                           locale="en", channel="email", subject="Payment received", body="Your payment succeeded.",
                           version=1, is_active=True)
    pref = create_or_first("notificationsapp.NotificationPreference", tenant=tenant, user_id=user.id, channel="email", is_enabled=True)
    disp = create_or_first("notificationsapp.NotificationDispatch", tenant=tenant, template=tmpl, to_user_id=user.id,
                           to_address=user.email, channel="email", payload_json={"order_id": str(order.id)}, status="queued")
    create_or_first("notificationsapp.NotificationLog", tenant=tenant, dispatch=disp, provider="console", status="sent", provider_ref="log1")

    # ---------- Marketing ----------
    create_or_first("marketing.Segment", tenant=tenant, name="High-value", definition_json={"min_spend": 500})
    create_or_first("marketing.Campaign", tenant=tenant, name="Welcome Email", channel="email", status="draft")

    # ---------- Analytics / AI ----------
    CdpProfile = M("analyticsapp.CdpProfile"); Event = M("analyticsapp.Event")
    prof = create_or_first("analyticsapp.CdpProfile", tenant=tenant, customer=cust, traits_json={"lifetime_value": 1000})
    create_or_first("analyticsapp.Event", tenant=tenant, profile=prof, name="order_placed", props={"order_id": str(order.id)})

    AiModel = M("aiapp.AiModel"); AiJob = M("aiapp.AiJob"); AiPrediction = M("aiapp.AiPrediction"); AiRecommendation = M("aiapp.AiRecommendation")
    aim = create_or_first("aiapp.AiModel", tenant=tenant, name="recommender", version="1.0", task="recommendation", is_active=True)
    aij = create_or_first("aiapp.AiJob", tenant=tenant, model=aim, job_type="infer", entity_type="order", entity_id=order.id, status="queued")
    aip = create_or_first("aiapp.AiPrediction", tenant=tenant, model=aim, entity_type="customer", entity_id=cust.id, score=Decimal("0.823"))
    air = create_or_first("aiapp.AiRecommendation", tenant=tenant, model=aim, customer=cust, context="homepage",
                          items_json=[{"sku":"X-BLK-128","reason":"similar_buyers"}])

    # ---------- Identity (API client / OAuth provider) ----------
    create_or_first("identity.ApiClient", tenant=tenant, name="CLI", key="dev-api-key", scopes=["read","write"])
    create_or_first("identity.OAuthProvider", tenant=tenant, kind="google", config={"enabled": True})

    # ---------- Support ----------
    create_or_first("support.Ticket", tenant=tenant, customer=cust, subject="Order question", status="open", priority="medium")
    create_or_first("support.KBArticle", tenant=tenant, title="How to track your order", body="Go to /orders.", is_published=True)

    # ---------- Platform audit ----------
    create_or_first("platformapp.AuditLog", tenant=tenant, user_id=user.id, action="seed",
                    entity="Tenant", entity_id=str(tenant.id), meta_json={"note":"initial seed"})

seed()
print("✓ Seed complete.")
PY

echo "==> Done. Try:"
echo "  • Admin: /admin/"
echo "  • Products: /admin/commerce/product/"
echo "  • Orders: /admin/commerce/order/"
echo "  • Inventory: /admin/inventory/stockreservation/"
