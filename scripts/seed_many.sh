#!/usr/bin/env bash
set -euo pipefail

PYBIN="${PYBIN:-python}"
MANAGE="backend/manage.py"
SEED_COUNT="${SEED_COUNT:-20}"

echo "==> migrate"
$PYBIN "$MANAGE" migrate --noinput

echo "==> seed $SEED_COUNT+ rich dataset"
$PYBIN "$MANAGE" shell <<'PY'
import uuid, random
from decimal import Decimal
from django.utils import timezone
from django.apps import apps
from django.db import transaction
from django.contrib.auth import get_user_model

def M(label): return apps.get_model(label)
def fset(model): 
    return {f.name for f in model._meta.get_fields() if getattr(f,"concrete",True) and not getattr(f,"many_to_many",False)}
def first_or_create(label, **kwargs):
    m = M(label)
    # try to find a stable unique key
    key_candidates = [k for k in ("slug","email","sku","code","number","key","template_key","name","url") if k in kwargs]
    q = {k:kwargs[k] for k in key_candidates}
    obj = m.objects.filter(**q).first() if q else m.objects.filter(**kwargs).first()
    return obj or m.objects.create(**kwargs)

@transaction.atomic
def seed(N=20):
    rnd = random.Random(42)
    now = timezone.now()
    User = get_user_model()

    tenant = first_or_create("platformapp.Tenant", slug="acme", name="ACME Corp", plan="pro", region="us")
    role_owner = first_or_create("platformapp.Role", tenant=tenant, name="owner", scope_level="business")
    admin = User.objects.filter(email="admin@acme.test").first()
    if not admin:
        admin = User.objects.create_superuser(email="admin@acme.test", password="Admin123!", full_name="ACME Admin")
    first_or_create("platformapp.UserRole", tenant=tenant, role=role_owner, user_id=admin.id)

    site = first_or_create("sites.Site", domain="localhost:8080", name="Local Dev")
    first_or_create("account.EmailAddress", user=admin, email=admin.email, verified=True, primary=True)
    first_or_create("identity.ApiClient", tenant=tenant, name="CLI", key="dev-api-key", scopes=["read","write"])
    first_or_create("identity.OAuthProvider", tenant=tenant, kind="google", config={"enabled": True})

    ind   = first_or_create("taxonomy.Industry", tenant=tenant, name="Retail", slug="retail")
    cats  = [first_or_create("taxonomy.Category", tenant=tenant, industry=ind, name=f"Category {i+1}", slug=f"cat-{i+1}") for i in range(5)]
    subs  = []
    for i, c in enumerate(cats, start=1):
        for j in range(2):
            subs.append(first_or_create("taxonomy.Subcategory", tenant=tenant, category=c, name=f"{c.name} Sub{j+1}", slug=f"{c.slug}-sub{j+1}"))

    addr  = first_or_create("business.Address", tenant=tenant, line1="100 Main St", city="Metropolis", country="US")
    biz   = first_or_create("business.Business", tenant=tenant, name="ACME Stores", url_slug="acme", currency="USD")
    stores= [
        first_or_create("business.Store", tenant=tenant, business=biz, name="ACME HQ", type="office", url_slug="hq", address=addr),
        first_or_create("business.Store", tenant=tenant, business=biz, name="ACME Downtown", type="retail", url_slug="downtown", address=addr),
        first_or_create("business.Store", tenant=tenant, business=biz, name="ACME Airport", type="retail", url_slug="airport", address=addr),
    ]

    for i in range(5):
        first_or_create("hr.Employee", tenant=tenant, business=biz, store=stores[0],
                        first_name=f"Emp{i+1}", last_name="Tester", email=f"emp{i+1}@acme.test", status="active")

    customers=[]
    for i in range(N):
        cust = first_or_create("crm.Customer", tenant=tenant, type="person",
                               name=f"Customer {i+1}", email=f"cust{i+1}@example.test", phone=f"+1-555-01{i:02d}")
        first_or_create("crm.Contact", tenant=tenant, customer=cust, first_name=f"Cust{i+1}", last_name="Contact",
                        email=cust.email, phone=f"+1-555-77{i:02d}")
        customers.append(cust)
    pipeline = first_or_create("crm.Pipeline", tenant=tenant, name="Default Sales")
    for i in range(N//2):
        first_or_create("crm.Opportunity", tenant=tenant, pipeline=pipeline, name=f"Opp {i+1}", amount=1000+i*50, stage="new")
    for c in customers[:10]:
        first_or_create("crm.Activity", tenant=tenant, customer=c, kind="note", content=f"Note for {c.name}")

    Product = M("commerce.Product"); Variant = M("commerce.Variant")
    Image   = M("commerce.ProductImage"); Video = M("commerce.ProductVideo")
    products, variants = [], []
    for i in range(N):
        p = first_or_create("commerce.Product", tenant=tenant, business=biz, name=f"Gadget {i+1}",
                            type="physical", default_price=Decimal("99.00")+i, currency="USD", is_active=True)
        products.append(p)
        # images
        first_or_create("commerce.ProductImage", tenant=tenant, product=p, url=f"https://pics.example/g{i+1}-1.jpg", alt_text="Front", position=1)
        first_or_create("commerce.ProductImage", tenant=tenant, product=p, url=f"https://pics.example/g{i+1}-2.jpg", alt_text="Back", position=2)
        # videos (no title; use provider+position)
        first_or_create("commerce.ProductVideo", tenant=tenant, product=p, url=f"https://video.example/g{i+1}.mp4", provider="cdn", position=1)
        # variants
        for cap in (64,128):
            v = first_or_create("commerce.Variant", tenant=tenant, product=p, sku=f"G{i+1}-BLK-{cap}",
                                price=p.default_price + (Decimal("20.00") if cap==128 else Decimal("0")), is_active=True)
            variants.append(v)

    Warehouse    = M("inventory.Warehouse"); StockItem = M("inventory.StockItem")
    StockLedger  = M("inventory.StockLedger"); StockReservation = M("inventory.StockReservation")
    wh1 = first_or_create("inventory.Warehouse", tenant=tenant, store=stores[0], name="WH-HQ")
    wh2 = first_or_create("inventory.Warehouse", tenant=tenant, store=stores[1], name="WH-Downtown")
    for v in variants:
        for (wh, qty) in ((wh1, 50), (wh2, 30)):
            si = StockItem.objects.filter(tenant=tenant, warehouse=wh, variant=v).first()
            if not si:
                si = StockItem.objects.create(tenant=tenant, warehouse=wh, variant=v, qty_on_hand=qty, qty_reserved=0)
                StockLedger.objects.create(tenant=tenant, warehouse=wh, variant=v, qty_delta=qty, reason="seed")
            elif si.qty_on_hand < 5:
                delta = 20
                si.qty_on_hand += delta
                si.save(update_fields=["qty_on_hand"])
                StockLedger.objects.create(tenant=tenant, warehouse=wh, variant=v, qty_delta=delta, reason="topup")

    Cart      = M("commerce.Cart"); CartItem   = M("commerce.CartItem")
    Order     = M("commerce.Order"); OrderItem = M("commerce.OrderItem")
    for i in range(N):
        cust = customers[i % len(customers)]
        cart = first_or_create("commerce.Cart", tenant=tenant, customer=cust, status="open")
        for _ in range(1 + (i % 3)):
            v = random.choice(variants)
            price = v.price or v.product.default_price
            first_or_create("commerce.CartItem", tenant=tenant, cart=cart, variant=v, qty=1 + (i % 2), price=price)

    orders=[]
    for i in range(N):
        cust = customers[i % len(customers)]
        order = first_or_create("commerce.Order", tenant=tenant, business=biz, customer=cust,
                                status="pending", total_amount=Decimal("0.00"), currency="USD")
        orders.append(order)
        picked = random.sample(variants, 2)
        oitems=[]
        for v in picked:
            price = v.price or v.product.default_price
            oi = first_or_create("commerce.OrderItem", tenant=tenant, order=order, variant=v, qty=1, price=price)
            oitems.append(oi)
            # reservation (requires order_item, not null)
            si1 = StockItem.objects.get(tenant=tenant, warehouse=wh1, variant=v)
            si2 = StockItem.objects.get(tenant=tenant, warehouse=wh2, variant=v)
            use_wh = wh1 if si1.qty_on_hand - si1.qty_reserved >= 1 else wh2
            StockReservation.objects.get_or_create(
                tenant=tenant, warehouse=use_wh, variant=v, order_item=oi, defaults={"qty": oi.qty}
            )
        total = sum(Decimal(str(i.price))*i.qty for i in OrderItem.objects.filter(order=order))
        if total and order.total_amount != total:
            order.total_amount = total
            order.save(update_fields=["total_amount"])

    GatewayAccount = M("payments.GatewayAccount"); Payment = M("payments.Payment")
    Refund = M("payments.Refund"); Payout = M("payments.Payout")
    ga = first_or_create("payments.GatewayAccount", tenant=tenant, kind="card",
                         config={"provider":"stripe","mode":"test"})
    TaxRate = M("invoicing.TaxRate"); Invoice = M("invoicing.Invoice")
    tax = first_or_create("invoicing.TaxRate", tenant=tenant, country="US", name="Sales Tax", rate=Decimal("0.0700"))
    for k, order in enumerate(orders[:N]):
        p = first_or_create("payments.Payment", tenant=tenant, order=order,
                            amount=order.total_amount, currency="USD",
                            status=("succeeded" if k%2==0 else "initiated"),
                            provider="card", provider_ref=f"pm_auto_{k+1}")
        first_or_create("invoicing.Invoice", tenant=tenant, order=order, number=f"INV-{k+1:04d}",
                        total_amount=(order.total_amount or Decimal("0.00")) * Decimal("1.07"),
                        currency="USD", status=("open" if k%2 else "paid"))

    PickupCenter = M("shipments.PickupCenter"); Shipment = M("shipments.Shipment"); ShipmentItem = M("shipments.ShipmentItem")
    pc = first_or_create("shipments.PickupCenter", tenant=tenant, code="PC001", name="ACME Pickup", lat=0.0, lng=0.0)
    fields_si = fset(ShipmentItem)
    for k, order in enumerate(orders):
        if k % 2 == 0:
            shp = first_or_create("shipments.Shipment", tenant=tenant, order=order, pickup_center=pc, status="ready", tracking=f"TRK{k+1:06d}")
            for oi in M("commerce.OrderItem").objects.filter(order=order):
                args = {"tenant":tenant, "shipment":shp, "qty":oi.qty}
                if "order" in fields_si: args["order"]=order
                if "order_item" in fields_si: args["order_item"]=oi
                if "variant" in fields_si: args["variant"]=oi.variant
                first_or_create("shipments.ShipmentItem", **args)

    for p in products[:10]:
        first_or_create("commerce.Review", tenant=tenant, product=p, rating=5, comment=f"Loved {p.name}")

    tmpl = first_or_create("notificationsapp.NotificationTemplate", tenant=tenant, template_key="payment_succeeded",
                           locale="en", channel="email", subject="Payment received", body="Your payment succeeded.",
                           version=1, is_active=True)
    first_or_create("notificationsapp.NotificationPreference", tenant=tenant, user_id=admin.id, channel="email", is_enabled=True)
    for i in range(5):
        disp = first_or_create("notificationsapp.NotificationDispatch", tenant=tenant, template=tmpl,
                               to_user_id=admin.id, to_address=admin.email, channel="email",
                               payload_json={"i":i}, status="queued")
        first_or_create("notificationsapp.NotificationLog", tenant=tenant, dispatch=disp, provider="console", status="sent", provider_ref=f"log{i+1}")

    for i in range(3):
        first_or_create("marketing.Segment", tenant=tenant, name=f"Segment {i+1}", definition_json={"i":i})
    for i in range(3):
        first_or_create("marketing.Campaign", tenant=tenant, name=f"Campaign {i+1}", channel="email", status="draft")

    CdpProfile = M("analyticsapp.CdpProfile"); Event = M("analyticsapp.Event")
    profiles=[]
    for c in customers[:N]:
        profiles.append(first_or_create("analyticsapp.CdpProfile", tenant=tenant, customer=c, traits_json={"lv": rnd.randint(100,2000)}))
    for i in range(N*2):
        first_or_create("analyticsapp.Event", tenant=tenant, profile=random.choice(profiles), name=random.choice(["page_view","add_to_cart","order_placed"]), props={"i":i})

    AiModel = M("aiapp.AiModel"); AiJob = M("aiapp.AiJob"); AiPrediction = M("aiapp.AiPrediction"); AiRecommendation = M("aiapp.AiRecommendation")
    aim = first_or_create("aiapp.AiModel", tenant=tenant, name="recommender", version="1.0", task="recommendation", is_active=True)
    for i in range(N):
        first_or_create("aiapp.AiJob", tenant=tenant, model=aim, job_type=random.choice(["train","infer"]), entity_type="order", entity_id=orders[i%len(orders)].id, status=random.choice(["queued","running","succeeded"]))
    for c in customers[:N]:
        first_or_create("aiapp.AiPrediction", tenant=tenant, model=aim, entity_type="customer", entity_id=c.id, score=Decimal(f"0.{random.randint(100000,999999)}"))
        first_or_create("aiapp.AiRecommendation", tenant=tenant, model=aim, customer=c, context="homepage",
                        items_json=[{"sku": random.choice(variants).sku, "reason": "similar_buyers"}])

    for i in range(5):
        first_or_create("support.Ticket", tenant=tenant, customer=random.choice(customers), subject=f"Ticket {i+1}", status="open", priority="medium")
    first_or_create("support.KBArticle", tenant=tenant, title="Shipping Times", body="Usually 2–5 days.", is_published=True)
    first_or_create("platformapp.AuditLog", tenant=tenant, user_id=admin.id, action="seed_many", entity="Tenant", entity_id=str(tenant.id), meta_json={"note":"bulk seed"})

seed(N=int(__import__("os").environ.get("SEED_COUNT","20")))
print("✓ Seeded many records.")
PY

echo "==> Done. Try:"
echo "  • Admin: /admin/"
echo "  • Products: /admin/commerce/product/"
echo "  • Orders:   /admin/commerce/order/"
echo "  • Inventory: /admin/inventory/stockreservation/"
