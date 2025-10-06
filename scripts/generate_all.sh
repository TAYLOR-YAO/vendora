#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
BACKEND_DIR="$ROOT/backend"
[ -d "$BACKEND_DIR" ] || { echo "ERR: run from repo root (where ./backend exists)"; exit 1; }

echo "==> Generating backend scaffold (models/serializers/views/urls/admin + business rules)..."

python3 - <<'PY'
import textwrap, pathlib, re, json, sys

root = pathlib.Path('.')
def W(path, content):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    print("wrote", path)

# ---------------------------
# Common utils
# ---------------------------
W("backend/common/__init__.py", "")
W("backend/common/models.py", """
from django.db import models
import uuid

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True
""")
W("backend/common/permissions.py", """
from rest_framework.permissions import BasePermission
class IsTenantUser(BasePermission):
    \"\"\"Dev-only: allow all (swap with real auth later).\"\"\"
    def has_permission(self, request, view): return True
""")
W("backend/common/mixins.py", """
from rest_framework import viewsets
class TenantScopedModelViewSet(viewsets.ModelViewSet):
    \"\"\"If ?tenant=<uuid> and model has 'tenant' FK, scope queryset.\"\"\"
    def get_queryset(self):
        qs = super().get_queryset()
        t = self.request.query_params.get("tenant")
        if t and hasattr(qs.model, "tenant"): return qs.filter(tenant_id=t)
        return qs
""")

# ---------------------------
# App skeletons (admin/urls placeholders)
# ---------------------------
APPS = [
 "core","platformapp","identity","taxonomy","business","crm","commerce","payments",
 "inventory","shipments","hr","invoicing","appointments","notificationsapp",
 "support","marketing","analyticsapp","aiapp"
]
for app in APPS:
    W(f"backend/{app}/__init__.py", "")
    # AppConfig (explicit for commerce/payments to load signals in ready())
    appcfg_name = f"{app.capitalize()}Config"
    W(f"backend/{app}/apps.py", f"""
from django.apps import AppConfig
class {appcfg_name}(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "{app}"
    def ready(self):
        try:
            from . import signals  # noqa
        except Exception:
            pass
""")
    # admin auto-register
    W(f"backend/{app}/admin.py", """
from django.contrib import admin
from django.apps import apps
from django.contrib.admin.sites import AlreadyRegistered
app = apps.get_app_config(__package__.split('.')[0])
for model in app.get_models():
    try: admin.site.register(model)
    except AlreadyRegistered: pass
""")
    # urls placeholder; will be overwritten by per-app routers below
    W(f"backend/{app}/urls.py", """
from django.urls import path, include
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
urlpatterns = [path('', include(router.urls))]
""")
    W(f"backend/{app}/serializers.py", "# generated below\n")
    W(f"backend/{app}/views.py", "# generated below\n")

# ---------------------------
# MODELS (ERD) with reservations/backorders/fulfillment
# ---------------------------
# platform
W("backend/platformapp/models.py", """
from django.db import models
from common.models import BaseModel

class Tenant(BaseModel):
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, default="active")
    plan = models.CharField(max_length=20, default="free")
    region = models.CharField(max_length=50, blank=True, null=True)

class Role(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="roles")
    name = models.CharField(max_length=100)
    scope_level = models.CharField(max_length=20, default="business")

class UserRole(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="user_roles")
    user_id = models.UUIDField()
    role = models.ForeignKey("platformapp.Role", on_delete=models.CASCADE)
    business_id = models.UUIDField(blank=True, null=True)
    store_id = models.UUIDField(blank=True, null=True)

class AuditLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="audit_logs")
    user_id = models.UUIDField(blank=True, null=True)
    action = models.CharField(max_length=80)
    entity = models.CharField(max_length=120)
    entity_id = models.CharField(max_length=120)
    meta_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
""")

# identity
W("backend/identity/models.py", """
from django.db import models
from common.models import BaseModel
class ApiClient(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="api_clients")
    name = models.CharField(max_length=120)
    key = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list, blank=True)
class OAuthProvider(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="oauth_providers")
    kind = models.CharField(max_length=20)
    config = models.JSONField(default=dict, blank=True)
""")

# taxonomy
W("backend/taxonomy/models.py", """
from django.db import models
from common.models import BaseModel
class Industry(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="industries")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
class Category(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="categories")
    industry = models.ForeignKey("taxonomy.Industry", on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
class Subcategory(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="subcategories")
    category = models.ForeignKey("taxonomy.Category", on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
""")

# business (with backorder flag)
W("backend/business/models.py", """
from django.db import models
from common.models import BaseModel
class Address(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="addresses")
    line1 = models.CharField(max_length=200)
    line2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=80)
    country = models.CharField(max_length=2, default="TG")
    lat = models.FloatField(blank=True, null=True)
    lng = models.FloatField(blank=True, null=True)
class Business(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="businesses")
    name = models.CharField(max_length=200)
    url_slug = models.SlugField(max_length=120)
    currency = models.CharField(max_length=3, default="XOF")
    settings_json = models.JSONField(default=dict)
    allow_backorder = models.BooleanField(default=False)  # NEW
class Store(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="stores")
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE, related_name="stores")
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=32, default="store")
    url_slug = models.SlugField(max_length=120, blank=True, null=True)
    address = models.ForeignKey("business.Address", on_delete=models.SET_NULL, blank=True, null=True)
""")

# crm
W("backend/crm/models.py", """
from django.db import models
from common.models import BaseModel
class Customer(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="customers")
    type = models.CharField(max_length=20, default="person")
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
class Contact(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="contacts")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, blank=True, null=True, related_name="contacts")
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
class Pipeline(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="pipelines")
    name = models.CharField(max_length=120)
class Opportunity(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="opportunities")
    pipeline = models.ForeignKey("crm.Pipeline", on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    stage = models.CharField(max_length=32, default="new")
    owner_user_id = models.UUIDField(blank=True, null=True)
class Activity(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="activities")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=20, default="note")
    content = models.TextField(blank=True, null=True)
""")

# commerce (plain models; business rules live in signals)
W("backend/commerce/models.py", """
from django.db import models
from common.models import BaseModel
class Product(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="products")
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, default="physical")
    default_price = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="XOF")
    is_active = models.BooleanField(default=True)
class Variant(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="variants")
    product = models.ForeignKey("commerce.Product", on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=120, unique=True)
    price = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
class Cart(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="carts")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=16, default="open")
class CartItem(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="cart_items")
    cart = models.ForeignKey("commerce.Cart", on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("commerce.Variant", on_delete=models.CASCADE)
    qty = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=18, decimal_places=2)
class Order(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="orders")
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE, related_name="orders")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default="pending")
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="XOF")
class OrderItem(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="order_items")
    order = models.ForeignKey("commerce.Order", on delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("commerce.Variant", on_delete=models.CASCADE)
    qty = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=18, decimal_places=2)
class Review(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey("commerce.Product", on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(default=5)
    comment = models.TextField(blank=True, null=True)
""".replace(" on delete", " on_delete"))  # fix typo if any

# payments
W("backend/payments/models.py", """
from django.db import models
from common.models import BaseModel
class GatewayAccount(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="gateway_accounts")
    kind = models.CharField(max_length=20)
    config = models.JSONField(default=dict)
class Payment(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="payments")
    order = models.ForeignKey("commerce.Order", on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="XOF")
    status = models.CharField(max_length=20, default="initiated")
    provider = models.CharField(max_length=40, default="card")
    provider_ref = models.CharField(max_length=120, blank=True, null=True)
    meta_json = models.JSONField(default=dict, blank=True)
class Refund(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="refunds")
    payment = models.ForeignKey("payments.Payment", on_delete=models.CASCADE, related_name="refunds")
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, default="pending")
class Payout(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="payouts")
    gateway_account = models.ForeignKey("payments.GatewayAccount", on_delete=models.CASCADE, related_name="payouts")
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, default="pending")
""")

# inventory (with qty_reserved + StockReservation)
W("backend/inventory/models.py", """
from django.db import models
from common.models import BaseModel
class Warehouse(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="warehouses")
    store = models.ForeignKey("business.Store", on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
class StockItem(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="stock_items")
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.CASCADE, related_name="stock_items")
    variant = models.ForeignKey("commerce.Variant", on_delete=models.CASCADE)
    qty_on_hand = models.IntegerField(default=0)
    qty_reserved = models.IntegerField(default=0)  # NEW
class StockLedger(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="stock_ledgers")
    variant = models.ForeignKey("commerce.Variant", on_delete=models.CASCADE)
    qty_delta = models.IntegerField()
    reason = models.CharField(max_length=64, default="adjustment")
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.SET_NULL, null=True, blank=True)
    order_item_id = models.UUIDField(null=True, blank=True)
class StockReservation(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="stock_reservations")
    order_item = models.ForeignKey("commerce.OrderItem", on_delete=models.CASCADE, related_name="reservations")
    variant = models.ForeignKey("commerce.Variant", on_delete=models.CASCADE)
    warehouse = models.ForeignKey("inventory.Warehouse", on_delete=models.CASCADE)
    qty = models.IntegerField()
    status = models.CharField(max_length=16, default="reserved")  # reserved|consumed|released
""")

# shipments (with ShipmentItem)
W("backend/shipments/models.py", """
from django.db import models
from common.models import BaseModel
class PickupCenter(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="pickup_centers")
    code = models.CharField(max_length=16)
    name = models.CharField(max_length=200)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
class Shipment(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="shipments")
    order = models.ForeignKey("commerce.Order", on_delete=models.CASCADE, related_name="shipments")
    address = models.ForeignKey("business.Address", on_delete=models.SET_NULL, null=True, blank=True)
    pickup_center = models.ForeignKey("shipments.PickupCenter", on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default="pending")  # pending | fulfilled | partial | cancelled
    tracking = models.CharField(max_length=64, blank=True, null=True)
class ShipmentItem(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="shipment_items")
    shipment = models.ForeignKey("shipments.Shipment", on_delete=models.CASCADE, related_name="items")
    order_item = models.ForeignKey("commerce.OrderItem", on_delete=models.CASCADE, related_name="shipment_items")
    variant = models.ForeignKey("commerce.Variant", on_delete=models.CASCADE)
    qty = models.IntegerField()
    status = models.CharField(max_length=16, default="pending")  # pending|fulfilled|cancelled
""")

# hr
W("backend/hr/models.py", """
from django.db import models
from common.models import BaseModel
class Employee(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="employees")
    business = models.ForeignKey("business.Business", on_delete=models.CASCADE, related_name="employees")
    store = models.ForeignKey("business.Store", on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
    status = models.CharField(max_length=20, default="active")
""")

# invoicing
W("backend/invoicing/models.py", """
from django.db import models
from common.models import BaseModel
class TaxRate(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="tax_rates")
    country = models.CharField(max_length=2, default="TG")
    name = models.CharField(max_length=80)
    rate = models.DecimalField(max_digits=6, decimal_places=4)
class Invoice(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="invoices")
    order = models.ForeignKey("commerce.Order", on_delete=models.CASCADE, related_name="invoices")
    number = models.CharField(max_length=50)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="XOF")
    status = models.CharField(max_length=20, default="open")
    pdf_url = models.URLField(blank=True, null=True)
""")

# appointments
W("backend/appointments/models.py", """
from django.db import models
from common.models import BaseModel
class Resource(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="resources")
    type = models.CharField(max_length=20, default="staff")
    name = models.CharField(max_length=200)
class Booking(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="bookings")
    resource = models.ForeignKey("appointments.Resource", on_delete=models.CASCADE, related_name="bookings")
    customer = models.ForeignKey("crm.Customer", on_delete=models.CASCADE, related_name="bookings")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(max_length=20, default="booked")
""")

# notifications
W("backend/notificationsapp/models.py", """
from django.db import models
from common.models import BaseModel
class NotificationTemplate(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="notif_templates")
    template_key = models.CharField(max_length=120)
    locale = models.CharField(max_length=10, default="en")
    channel = models.CharField(max_length=16, default="email")
    subject = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField()
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
class NotificationPreference(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="notif_prefs")
    user_id = models.UUIDField()
    channel = models.CharField(max_length=16, default="email")
    is_enabled = models.BooleanField(default=True)
    quiet_hours_json = models.JSONField(blank=True, null=True)
class NotificationDispatch(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="notif_dispatches")
    template = models.ForeignKey("notificationsapp.NotificationTemplate", on_delete=models.SET_NULL, null=True, blank=True)
    to_user_id = models.UUIDField(blank=True, null=True)
    to_address = models.CharField(max_length=255, blank=True, null=True)
    channel = models.CharField(max_length=16, default="email")
    payload_json = models.JSONField(default=dict)
    status = models.CharField(max_length=16, default="queued")
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)
class NotificationLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="notif_logs")
    dispatch = models.ForeignKey("notificationsapp.NotificationDispatch", on_delete=models.CASCADE, related_name="logs")
    provider = models.CharField(max_length=120)
    provider_ref = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=16, default="sent")
    meta_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
""")
W("backend/notificationsapp/utils.py", """
from .models import NotificationDispatch, NotificationLog
def queue_notification(tenant, template=None, to_user_id=None, to_address=None, channel="email", payload=None):
    return NotificationDispatch.objects.create(
        tenant=tenant, template=template, to_user_id=to_user_id,
        to_address=to_address, channel=channel, payload_json=payload or {}
    )
def log_delivery(dispatch, provider, status="sent", provider_ref=None, meta=None):
    return NotificationLog.objects.create(
        tenant=dispatch.tenant, dispatch=dispatch, provider=provider,
        status=status, provider_ref=provider_ref, meta_json=meta or {}
    )
""")

# support
W("backend/support/models.py", """
from django.db import models
from common.models import BaseModel
class Ticket(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="tickets")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=16, default="open")
    priority = models.CharField(max_length=16, default="medium")
class KBArticle(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="kb_articles")
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_published = models.BooleanField(default=False)
""")

# marketing
W("backend/marketing/models.py", """
from django.db import models
from common.models import BaseModel
class Segment(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="segments")
    name = models.CharField(max_length=200)
    definition_json = models.JSONField(default=dict)
class Campaign(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField(max_length=200)
    channel = models.CharField(max_length=16, default="email")
    content = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=16, default="draft")
""")

# analytics
W("backend/analyticsapp/models.py", """
from django.db import models
from common.models import BaseModel
class CdpProfile(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="cdp_profiles")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="cdp_profiles")
    traits_json = models.JSONField(default=dict)
class Event(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="events")
    profile = models.ForeignKey("analyticsapp.CdpProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    name = models.CharField(max_length=120)
    ts = models.DateTimeField(auto_now_add=True)
    props = models.JSONField(default=dict)
""")

# ai
W("backend/aiapp/models.py", """
from django.db import models
from common.models import BaseModel
class AiModel(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=120)
    version = models.CharField(max_length=40)
    task = models.CharField(max_length=32)
    params_json = models.JSONField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
class AiJob(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE)
    model = models.ForeignKey("aiapp.AiModel", on_delete=models.CASCADE)
    job_type = models.CharField(max_length=16)
    entity_type = models.CharField(max_length=80, blank=True, null=True)
    entity_id = models.UUIDField(blank=True, null=True)
    status = models.CharField(max_length=16, default="queued")
    input_json = models.JSONField(blank=True, null=True)
    output_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
class AiPrediction(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE)
    model = models.ForeignKey("aiapp.AiModel", on_delete=models.CASCADE)
    entity_type = models.CharField(max_length=80)
    entity_id = models.UUIDField()
    score = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    explain_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
class AiRecommendation(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE)
    model = models.ForeignKey("aiapp.AiModel", on_delete=models.SET_NULL, null=True, blank=True)
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True)
    context = models.CharField(max_length=80)
    items_json = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
""")

# ---------------------------
# SERIALIZERS + VIEWSETS + URLS (generic for all apps)
# ---------------------------
from collections import OrderedDict
APP_MODELS = OrderedDict([
 ("platformapp", ["Tenant","Role","UserRole","AuditLog"]),
 ("identity", ["ApiClient","OAuthProvider"]),
 ("taxonomy", ["Industry","Category","Subcategory"]),
 ("business", ["Address","Business","Store"]),
 ("crm", ["Customer","Contact","Pipeline","Opportunity","Activity"]),
 ("commerce", ["Product","Variant","Cart","CartItem","Order","OrderItem","Review"]),
 ("payments", ["GatewayAccount","Payment","Refund","Payout"]),
 ("inventory", ["Warehouse","StockItem","StockLedger","StockReservation"]),
 ("shipments", ["Shipment","ShipmentItem","PickupCenter"]),
 ("hr", ["Employee"]),
 ("invoicing", ["TaxRate","Invoice"]),
 ("appointments", ["Resource","Booking"]),
 ("notificationsapp", ["NotificationTemplate","NotificationPreference","NotificationDispatch","NotificationLog"]),
 ("support", ["Ticket","KBArticle"]),
 ("marketing", ["Segment","Campaign"]),
 ("analyticsapp", ["CdpProfile","Event"]),
 ("aiapp", ["AiModel","AiJob","AiPrediction","AiRecommendation"]),
])

for app, models in APP_MODELS.items():
    # serializers
    s = ["from rest_framework import serializers", f"from .models import {', '.join(models)}", ""]
    for m in models:
        s.append(f"class {m}Serializer(serializers.ModelSerializer):\n    class Meta:\n        model = {m}\n        fields = '__all__'\n")
    W(f"backend/{app}/serializers.py", "\n".join(s))
    # views (generic ViewSets; shipments gets a custom below)
    if app != "shipments":
        v = ["from common.mixins import TenantScopedModelViewSet", f"from .models import {', '.join(models)}", f"from .serializers import {', '.join(m+'Serializer' for m in models)}", ""]
        for m in models:
            v.append(f"class {m}ViewSet(TenantScopedModelViewSet):\n    queryset = {m}.objects.all()\n    serializer_class = {m}Serializer\n")
        W(f"backend/{app}/views.py", "\n".join(v))

# shipments custom view with fulfill()
W("backend/shipments/serializers.py", """
from rest_framework import serializers
from .models import Shipment, ShipmentItem, PickupCenter
class ShipmentItemSerializer(serializers.ModelSerializer):
    class Meta: model = ShipmentItem; fields = "__all__"
class ShipmentSerializer(serializers.ModelSerializer):
    items = ShipmentItemSerializer(many=True, read_only=True)
    class Meta: model = Shipment; fields = "__all__"
class PickupCenterSerializer(serializers.ModelSerializer):
    class Meta: model = PickupCenter; fields = "__all__"
""")
W("backend/shipments/views.py", """
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from common.mixins import TenantScopedModelViewSet
from .models import Shipment, ShipmentItem, PickupCenter
from .serializers import ShipmentSerializer, ShipmentItemSerializer, PickupCenterSerializer
from inventory.models import StockItem, StockLedger, StockReservation

class ShipmentViewSet(TenantScopedModelViewSet):
    queryset = Shipment.objects.all()
    serializer_class = ShipmentSerializer

    @action(detail=True, methods=["post"])
    def fulfill(self, request, pk=None):
        shipment = self.get_object()
        tenant = shipment.tenant
        with transaction.atomic():
            for si in shipment.items.select_related("order_item","variant").all():
                if si.status == "fulfilled": continue
                remaining = si.qty
                reservations = (StockReservation.objects
                                .select_for_update()
                                .filter(tenant=tenant, order_item=si.order_item, variant=si.variant, status="reserved")
                                .select_related("warehouse")
                                .order_by("created_at"))
                for res in reservations:
                    if remaining <= 0: break
                    take = min(res.qty, remaining)
                    stock = StockItem.objects.select_for_update().get(
                        tenant=tenant, warehouse=res.warehouse, variant=si.variant
                    )
                    stock.qty_reserved = max(0, stock.qty_reserved - take)
                    stock.qty_on_hand -= take
                    stock.save(update_fields=["qty_reserved","qty_on_hand"])
                    StockLedger.objects.create(
                        tenant=tenant, variant=si.variant, qty_delta=-take, reason="consume",
                        warehouse=res.warehouse, order_item_id=si.order_item.id
                    )
                    res.qty -= take
                    res.status = "consumed" if res.qty == 0 else res.status
                    res.save(update_fields=["qty","status"])
                    remaining -= take
                si.status = "fulfilled"
                si.save(update_fields=["status"])
            shipment.status = "partial" if shipment.items.filter(status="pending").exists() else "fulfilled"
            shipment.save(update_fields=["status"])
        return Response({"ok": True, "shipment": ShipmentSerializer(shipment).data}, status=status.HTTP_200_OK)

class ShipmentItemViewSet(TenantScopedModelViewSet):
    queryset = ShipmentItem.objects.all()
    serializer_class = ShipmentItemSerializer

class PickupCenterViewSet(TenantScopedModelViewSet):
    queryset = PickupCenter.objects.all()
    serializer_class = PickupCenterSerializer
""")
W("backend/shipments/urls.py", """
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ShipmentViewSet, ShipmentItemViewSet, PickupCenterViewSet
router = DefaultRouter()
router.register(r'shipment', ShipmentViewSet)
router.register(r'shipmentitem', ShipmentItemViewSet)
router.register(r'pickupcenter', PickupCenterViewSet)
urlpatterns = [path('', include(router.urls))]
""")

# ---------------------------
# Commerce signals (reserve+recompute) & Payments signals (mark paid + notify)
# ---------------------------
W("backend/commerce/signals.py", """
from decimal import Decimal
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import Order, OrderItem
from business.models import Business
from inventory.models import StockItem, StockReservation, StockLedger

def _available(stock): return stock.qty_on_hand - stock.qty_reserved

def _allocate_reservations(tenant, order_item, preferred_warehouse_id=None, proportional=True, allow_backorder=False):
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
""")

W("backend/payments/signals.py", """
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment
from notificationsapp.utils import queue_notification

@receiver(post_save, sender=Payment)
def on_payment_success(sender, instance, created, **kwargs):
    if instance.status == "succeeded":
        order = instance.order
        if order.status != "paid":
            order.status = "paid"
            order.save(update_fields=["status"])
            queue_notification(tenant=order.tenant, channel="email",
                               payload={"type":"order_paid","order_id":str(order.id)})
""")

# ---------------------------
# URLs root + core health
# ---------------------------
W("backend/core/views.py", "from django.http import JsonResponse\ndef healthz(_): return JsonResponse({'ok': True})\n")
W("backend/core/urls.py", "from django.urls import path\nfrom .views import healthz\nurlpatterns=[path('healthz/', healthz)]\n")
W("backend/vendora_backend/urls.py", """
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
def root(_r): return JsonResponse({"service":"vendora-backend","docs":"/api/docs","health":"/api/v1/core/healthz/"})
urlpatterns = [
  path("", root),
  path("admin/", admin.site.urls),
  path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
  path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
  path("api/v1/core/", include("core.urls")),
  path("api/v1/platform/", include("platformapp.urls")),
  path("api/v1/identity/", include("identity.urls")),
  path("api/v1/taxonomy/", include("taxonomy.urls")),
  path("api/v1/business/", include("business.urls")),
  path("api/v1/crm/", include("crm.urls")),
  path("api/v1/commerce/", include("commerce.urls")),
  path("api/v1/payments/", include("payments.urls")),
  path("api/v1/inventory/", include("inventory.urls")),
  path("api/v1/shipments/", include("shipments.urls")),
  path("api/v1/hr/", include("hr.urls")),
  path("api/v1/invoicing/", include("invoicing.urls")),
  path("api/v1/appointments/", include("appointments.urls")),
  path("api/v1/notifications/", include("notificationsapp.urls")),
  path("api/v1/support/", include("support.urls")),
  path("api/v1/marketing/", include("marketing.urls")),
  path("api/v1/analytics/", include("analyticsapp.urls")),
  path("api/v1/ai/", include("aiapp.urls")),
]
""")

# ---------------------------
# Per-app routers (generic)
# ---------------------------
for app, models in APP_MODELS.items():
    if app == "shipments":  # already written
        continue
    lines = ["from rest_framework.routers import DefaultRouter","from django.urls import path, include"]
    for m in models:
        lines.append(f"from .views import {m}ViewSet")
    lines.append("\nrouter = DefaultRouter()")
    for m in models:
        lines.append(f"router.register(r'{m.lower()}', {m}ViewSet)")
    lines.append("\nurlpatterns = [ path('', include(router.urls)) ]")
    W(f"backend/{app}/urls.py", "\n".join(lines))

# ---------------------------
# Ensure AppConfig usage in settings.py for signals (idempotent)
# ---------------------------
settings_path = root / "backend/vendora_backend/settings.py"
if settings_path.exists():
    s = settings_path.read_text(encoding="utf-8")
    s = s.replace("'commerce',", "'commerce.apps.CommerceConfig',")
    s = s.replace('"commerce",', '"commerce.apps.CommerceConfig",')
    s = s.replace("'payments',", "'payments.apps.PaymentsConfig',")
    s = s.replace('"payments",', '"payments.apps.PaymentsConfig",')
    settings_path.write_text(s, encoding="utf-8")
    print("patched settings.py to use CommerceConfig/PaymentsConfig")
else:
    print("NOTE: backend/vendora_backend/settings.py not found to patch AppConfig (ok if already correct).")
PY

echo "==> Cleaning stale migration files (safe optional)..."
find backend -path "*/migrations/*.py" ! -name "__init__.py" -delete || true
find backend -path "*/migrations/*.pyc" -delete || true

echo "==> Makemigrations..."
python backend/manage.py makemigrations

echo "==> Migrate..."
python backend/manage.py migrate

echo "==> Done."
echo "Run dev server:"
echo "  python backend/manage.py runserver 0.0.0.0:8080"
echo "Health: /api/v1/core/healthz/"
