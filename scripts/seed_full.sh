#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="python"

# Ensure DB is migrated (safe to re-run)
$PYTHON_BIN backend/manage.py migrate

# Seed data (idempotent, adapts to your current schema)
$PYTHON_BIN backend/manage.py shell <<'PY'
from decimal import Decimal
from datetime import datetime, timedelta
from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.utils import timezone
from django.apps import apps

# --- Import all models ---
from platformapp.models import Tenant, Role, UserRole, AuditLog
from identity.models import ApiClient, OAuthProvider
from taxonomy.models import Industry, Category, Subcategory
from business.models import Business, Store, Address
from crm.models import Customer, Contact, Pipeline, Opportunity, Activity
from commerce.models import Product, Variant, Cart, CartItem, Order, OrderItem, Review
from payments.models import GatewayAccount, Payment, Refund, Payout
from inventory.models import Warehouse, StockItem
from shipments.models import Shipment, ShipmentItem, PickupCenter
from hr.models import Employee
from invoicing.models import TaxRate, Invoice
from appointments.models import Resource, Booking
from notificationsapp.models import NotificationTemplate, NotificationPreference, NotificationDispatch
from support.models import Ticket, KBArticle
from marketing.models import Segment, Campaign
from analyticsapp.models import CdpProfile, Event
from aiapp.models import AiModel, AiJob, AiPrediction, AiRecommendation

# Optional models that might not exist
ProductImage = apps.get_model('commerce', 'ProductImage', require_ready=False)
ProductVideo = apps.get_model('commerce', 'ProductVideo', require_ready=False)

User = get_user_model()

@transaction.atomic
def seed():
    print("--- Seeding Core Platform ---")
    # --- Tenant & Site ---
    tenant, _ = Tenant.objects.get_or_create(
        slug="vendora-demo",
        defaults=dict(name="Vendora Demo", status="active", plan="enterprise")
    )
    Site.objects.get_or_create(id=1, defaults={'domain': 'demo.vendora.com', 'name': 'Vendora Demo'})

    # --- User, Roles, and Identity ---
    admin_user, _ = User.objects.get_or_create(
        email="admin@vendora.com",
        defaults=dict(username="admin", full_name="Admin User", is_staff=True, is_superuser=True)
    )
    if not admin_user.has_usable_password():
        admin_user.set_password("ChangeMe!123")
        admin_user.save()

    admin_role, _ = Role.objects.get_or_create(tenant=tenant, name="Administrator", defaults=dict(scope_level="platform"))
    store_manager_role, _ = Role.objects.get_or_create(tenant=tenant, name="Store Manager", defaults=dict(scope_level="business"))

    UserRole.objects.get_or_create(tenant=tenant, user_id=admin_user.id, role=admin_role)
    ApiClient.objects.get_or_create(tenant=tenant, name="Internal Reporting API", defaults=dict(key="int_rep_key_abc123"))
    OAuthProvider.objects.get_or_create(tenant=tenant, kind="google", defaults=dict(config={"client_id": "google-client-id"}))

    print("--- Seeding Business & HR ---")
    # --- Business, Store, Address ---
    hq_address, _ = Address.objects.get_or_create(tenant=tenant, line1="123 Vendora HQ", city="Lomé", country="TG")
    biz, _ = Business.objects.get_or_create(
        tenant=tenant, url_slug="demo-fashion",
        defaults=dict(name="Vendora Fashion", currency="XOF", allow_backorder=True)
    )
    main_store, _ = Store.objects.get_or_create(
        tenant=tenant, business=biz, name="Lomé Flagship Store",
        defaults=dict(type="retail", url_slug="lome-flagship", address=hq_address)
    )
    Employee.objects.get_or_create(
        tenant=tenant, business=biz, store=main_store, first_name="Afi", last_name="Manager",
        defaults=dict(email="manager@vendora.com", status="active")
    )

    print("--- Seeding CRM & Marketing ---")
    # --- Customer, Pipeline, Opportunity ---
    customer, _ = Customer.objects.get_or_create(
        tenant=tenant, email="customer@example.com",
        defaults=dict(type="person", name="John Doe", phone="+22890123456")
    )
    Contact.objects.get_or_create(tenant=tenant, customer=customer, first_name="John", last_name="Doe", email=customer.email)
    sales_pipeline, _ = Pipeline.objects.get_or_create(tenant=tenant, name="Sales Pipeline")
    Opportunity.objects.get_or_create(
        tenant=tenant, pipeline=sales_pipeline, name="Initial Deal with John Doe",
        defaults=dict(amount="50000", stage="prospecting", owner_user_id=admin_user.id)
    )
    Activity.objects.get_or_create(tenant=tenant, customer=customer, kind="email", defaults=dict(content="Sent welcome email."))
    Segment.objects.get_or_create(tenant=tenant, name="New Customers", defaults=dict(definition_json={"period": "last_30_days"}))
    Campaign.objects.get_or_create(tenant=tenant, name="Welcome Series", defaults=dict(channel="email", status="active"))

    print("--- Seeding Taxonomy & Commerce ---")
    # --- Taxonomy, Product, Variants ---
    industry, _ = Industry.objects.get_or_create(tenant=tenant, slug="fashion", defaults=dict(name="Fashion"))
    cat, _ = Category.objects.get_or_create(tenant=tenant, industry=industry, slug="apparel", defaults=dict(name="Apparel"))
    subcat, _ = Subcategory.objects.get_or_create(tenant=tenant, category=cat, slug="t-shirts", defaults=dict(name="T-Shirts"))

    product, _ = Product.objects.get_or_create(
        tenant=tenant, business=biz, name="Vendora Classic Tee",
        defaults=dict(type="physical", default_price="15000", currency="XOF")
    )
    if ProductImage:
        ProductImage.objects.get_or_create(tenant=tenant, product=product, url="https://example.com/tee.jpg", defaults=dict(alt_text="Classic Tee"))
    if ProductVideo:
        ProductVideo.objects.get_or_create(tenant=tenant, product=product, url="https://example.com/tee.mp4")

    variant_s, _ = Variant.objects.get_or_create(tenant=tenant, product=product, sku="VDR-TEE-S", defaults=dict(price="15000"))
    variant_m, _ = Variant.objects.get_or_create(tenant=tenant, product=product, sku="VDR-TEE-M", defaults=dict(price="15000"))
    Review.objects.get_or_create(tenant=tenant, product=product, defaults=dict(rating=5, comment="Excellent quality!"))

    print("--- Seeding Inventory ---")
    # --- Warehouse & Stock ---
    warehouse, _ = Warehouse.objects.get_or_create(tenant=tenant, store=main_store, name="Main Warehouse")
    StockItem.objects.get_or_create(tenant=tenant, warehouse=warehouse, variant=variant_s, defaults=dict(qty_on_hand=100))
    StockItem.objects.get_or_create(tenant=tenant, warehouse=warehouse, variant=variant_m, defaults=dict(qty_on_hand=150))

    print("--- Seeding Order & Fulfillment Flow ---")
    # --- Cart, Order, OrderItem ---
    # Note: The signals in commerce/signals.py will handle stock reservation and total calculation.
    cart, _ = Cart.objects.get_or_create(tenant=tenant, customer=customer, status="open")
    CartItem.objects.get_or_create(cart=cart, tenant=tenant, variant=variant_m, defaults=dict(qty=2, price="15000"))

    order, _ = Order.objects.get_or_create(
        tenant=tenant, business=biz, customer=customer, status="pending",
        defaults=dict(currency="XOF")
    )
    # Create OrderItem, which triggers signals
    order_item, created = OrderItem.objects.get_or_create(
        tenant=tenant, order=order, variant=variant_m,
        defaults=dict(qty=2, price="15000")
    )

    # --- Payment, Invoice, Refund, Payout ---
    gateway, _ = GatewayAccount.objects.get_or_create(tenant=tenant, kind="stripe", defaults=dict(config={"api_key": "sk_test_..."}))
    payment, _ = Payment.objects.get_or_create(
        tenant=tenant, order=order, amount=order.total_amount,
        defaults=dict(currency="XOF", status="succeeded", provider="stripe", provider_ref="pi_123")
    )
    Refund.objects.get_or_create(tenant=tenant, payment=payment, amount="5000", defaults=dict(status="processed"))
    Payout.objects.get_or_create(tenant=tenant, gateway_account=gateway, amount="100000", defaults=dict(status="paid"))
    TaxRate.objects.get_or_create(tenant=tenant, name="VAT", defaults=dict(country="TG", rate="0.18"))
    Invoice.objects.get_or_create(
        tenant=tenant, order=order, number=f"INV-{order.id.hex[:6].upper()}",
        defaults=dict(total_amount=order.total_amount, status="paid")
    )

    # --- Shipment ---
    pickup_center, _ = PickupCenter.objects.get_or_create(tenant=tenant, code="LOME-CTR", name="Lomé Central Pickup")
    shipment, _ = Shipment.objects.get_or_create(
        tenant=tenant, order=order,
        defaults=dict(address=hq_address, status="processing", tracking="SHP123")
    )
    ShipmentItem.objects.get_or_create(
        tenant=tenant, shipment=shipment, order_item=order_item, variant=variant_m,
        defaults=dict(qty=order_item.qty)
    )

    print("--- Seeding Support, Appointments, Notifications ---")
    # --- Support & Appointments ---
    Ticket.objects.get_or_create(
        tenant=tenant, customer=customer, subject="Inquiry about my order",
        defaults=dict(status="open", priority="normal")
    )
    KBArticle.objects.get_or_create(tenant=tenant, title="How to Return an Item", defaults=dict(body="...", is_published=True))
    resource, _ = Resource.objects.get_or_create(tenant=tenant, name="Styling Consultant", defaults=dict(type="personnel"))
    Booking.objects.get_or_create(
        tenant=tenant, resource=resource, customer=customer,
        defaults=dict(start_at=timezone.now() + timedelta(days=3), end_at=timezone.now() + timedelta(days=3, hours=1))
    )

    # --- Notifications ---
    template, _ = NotificationTemplate.objects.get_or_create(
        tenant=tenant, template_key="order.shipped",
        defaults=dict(channel="email", subject="Your order has shipped!", body="Hi {{name}}, your order {{order_id}} is on its way.")
    )
    NotificationPreference.objects.get_or_create(tenant=tenant, user_id=admin_user.id, defaults=dict(channel="email", is_enabled=True))
    NotificationDispatch.objects.get_or_create(
        tenant=tenant, template=template, to_address=customer.email,
        defaults=dict(payload_json={"name": customer.name, "order_id": order.id.hex[:8]})
    )

    print("--- Seeding Analytics & AI ---")
    # --- Analytics & AI ---
    profile, _ = CdpProfile.objects.get_or_create(tenant=tenant, customer=customer)
    Event.objects.get_or_create(
        tenant=tenant, profile=profile, name="product_viewed",
        defaults=dict(props={"product_id": str(product.id)})
    )
    ai_model, _ = AiModel.objects.get_or_create(
        tenant=tenant, name="product_recommender",
        defaults=dict(version="v1.0", task="recommendation")
    )
    AiJob.objects.get_or_create(tenant=tenant, model=ai_model, job_type="train", defaults=dict(status="completed"))
    AiPrediction.objects.get_or_create(
        tenant=tenant, model=ai_model, entity_type="customer", entity_id=customer.id,
        defaults=dict(score="0.85")
    )
    AiRecommendation.objects.get_or_create(
        tenant=tenant, model=ai_model, customer=customer, context="homepage",
        defaults=dict(items_json=[{"sku": "VDR-TEE-S"}])
    )

    print("\n\033[1;32mSeed complete.\033[0m")
    print(f"Tenant: {tenant.name} ({tenant.id})")
    print(f"Admin User: {admin_user.email} (pw: ChangeMe!123)")
    print(f"Business: {biz.name} ({biz.id})")
    print(f"Order created: {order.id} for {order.total_amount} {order.currency}")

try:
    seed()
except Exception as e:
    print(f"\n\033[0;31mAn error occurred during seeding: {e}\033[0m")
    # Raising the exception will show the full traceback
    raise

PY

echo "OK — seed script executed."
echo "You can run this script again at any time to reset the data."
echo "Try API:"
echo "  /api/v1/commerce/product/?tenant=<TENANT_UUID>"
echo "  /api/v1/commerce/order/?tenant=<TENANT_UUID>"

```

### How to Use

1.  **Save the File**: Save the code above as `scripts/seed_full.sh` in your project's root directory.
2.  **Make it Executable**:
   ```bash
   chmod +x scripts/seed_full.sh
   ```
3.  **Run the Script**:
   ```bash
   ./scripts/seed_full.sh
   ```

This script will now create a rich, interconnected set of data across all your applications, giving you a solid foundation for development and testing.

<!--
[PROMPT_SUGGESTION]How can I write a test to confirm that the seeding script ran correctly?[/PROMPT_SUGGESTION]
[PROMPT_SUGGESTION]Explain the purpose of the `StockLedger` and `StockReservation` models.[/PROMPT_SUGGESTION]
