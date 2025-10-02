#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
[ -d "$ROOT/cloudbuild" ] || { echo "Run from your vendora repo root"; exit 1; }

python3 - <<'PY'
import os, textwrap, pathlib, json, sys
root = pathlib.Path('.')

def W(p, s):
    p = root / p
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(s).lstrip("\n"), encoding='utf-8')

# ------------------------------------------------------------
# Cloud Build & Deploy (minor upgrades)
# ------------------------------------------------------------
# Always-available tag for manual builds
def patch_build_id(p):
    s = (root/p).read_text()
    s = s.replace("$COMMIT_SHA", "$BUILD_ID")
    (root/p).write_text(s)
for p in ["cloudbuild/backend-cloudbuild.yaml","cloudbuild/frontend-cloudbuild.yaml"]:
    if (root/p).exists(): patch_build_id(p)

# Jobs pipeline (DB migrate / collectstatic)
W("cloudbuild/jobs-cloudbuild.yaml", """
steps:
  # Build backend image (re-usable for jobs)
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build','-t','africa-south1-docker.pkg.dev/$PROJECT_ID/vendora-docker/backend:$BUILD_ID','./backend']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push','africa-south1-docker.pkg.dev/$PROJECT_ID/vendora-docker/backend:$BUILD_ID']

  # Create/Update Cloud Run Job for migrations
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: bash
    args:
      - -c
      - |
        gcloud run jobs deploy vendora-migrate \\
          --region=africa-south1 \\
          --image=africa-south1-docker.pkg.dev/$PROJECT_ID/vendora-docker/backend:$BUILD_ID \\
          --service-account=vendora-backend-sa@$PROJECT_ID.iam.gserviceaccount.com \\
          --set-secrets=DJANGO_SECRET_KEY=vendora-django-secret:latest \\
          -- \\
          python manage.py migrate --noinput

  # Create/Update Cloud Run Job for collectstatic (optional)
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: bash
    args:
      - -c
      - |
        gcloud run jobs deploy vendora-collectstatic \\
          --region=africa-south1 \\
          --image=africa-south1-docker.pkg.dev/$PROJECT_ID/vendora-docker/backend:$BUILD_ID \\
          --service-account=vendora-backend-sa@$PROJECT_ID.iam.gserviceaccount.com \\
          --set-secrets=DJANGO_SECRET_KEY=vendora-django-secret:latest \\
          -- \\
          python manage.py collectstatic --noinput
""")

# Deploy/pinned manifests (optional to use later)
W("deploy/run/backend.service.yaml", """
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: vendora-backend
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/ingress: all
    spec:
      serviceAccountName: vendora-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com
      containers:
        - image: africa-south1-docker.pkg.dev/${PROJECT_ID}/vendora-docker/backend:${BUILD_ID}
          ports: [{containerPort: 8000}]
          env:
            - name: DJANGO_SETTINGS_MODULE
              value: vendora_backend.settings
            - name: DJANGO_DEBUG
              value: "false"
            - name: NEXT_PUBLIC_PLACEHOLDER
              value: "ok"
          envFrom: []
""")

# ------------------------------------------------------------
# Backend – add full module stubs (models/serializers/viewsets/urls)
# NOTE: These are robust CRUD stubs covering Bazario modules.
# ------------------------------------------------------------

base_models = """
from django.db import models
import uuid
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True
"""

W("backend/common/models.py", base_models)

# PLATFORM / TENANCY / RBAC
W("backend/platformapp/models.py", f"""
from django.db import models
from common.models import BaseModel

class Tenant(BaseModel):
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, default="active")
    plan = models.CharField(max_length=20, default="free")
    region = models.CharField(max_length=50, blank=True, null=True)

class Role(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="roles")
    name = models.CharField(max_length=100)
    scope_level = models.CharField(max_length=20, default="business")

class UserRole(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="user_roles")
    user_id = models.UUIDField()
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    business_id = models.UUIDField(blank=True, null=True)
    store_id = models.UUIDField(blank=True, null=True)

class AuditLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="audit_logs")
    user_id = models.UUIDField(blank=True, null=True)
    action = models.CharField(max_length=80)
    entity = models.CharField(max_length=120)
    entity_id = models.CharField(max_length=120)
    meta_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
""")

# Identity (auth endpoints placeholder – JWT to be added later)
W("backend/identity/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant

class ApiClient(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="api_clients")
    name = models.CharField(max_length=120)
    key = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list, blank=True)

class OAuthProvider(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="oauth_providers")
    kind = models.CharField(max_length=20)  # google, microsoft, saml
    config = models.JSONField(default=dict, blank=True)
""")

# Taxonomy
W("backend/taxonomy/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant

class Industry(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="industries")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)

class Category(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="categories")
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)

class Subcategory(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="subcategories")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
""")

# Business & Stores
W("backend/business/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant

class Address(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="addresses")
    line1 = models.CharField(max_length=200)
    line2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=80)
    country = models.CharField(max_length=2, default="TG")
    lat = models.FloatField(blank=True, null=True)
    lng = models.FloatField(blank=True, null=True)

class Business(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="businesses")
    name = models.CharField(max_length=200)
    url_slug = models.SlugField(max_length=120)
    currency = models.CharField(max_length=3, default="XOF")
    settings_json = models.JSONField(default=dict)

class Store(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="stores")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="stores")
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=32, default="store")
    url_slug = models.SlugField(max_length=120, blank=True, null=True)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, blank=True, null=True)
""")

# CRM
W("backend/crm/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant

class Customer(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="customers")
    type = models.CharField(max_length=20, default="person")
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)

class Contact(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="contacts")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, blank=True, null=True, related_name="contacts")
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)

class Pipeline(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="pipelines")
    name = models.CharField(max_length=120)

class Opportunity(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="opportunities")
    pipeline = models.ForeignKey(Pipeline, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    stage = models.CharField(max_length=32, default="new")
    owner_user_id = models.UUIDField(blank=True, null=True)

class Activity(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="activities")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=20, default="note")  # note, call, email
    content = models.TextField(blank=True, null=True)
""")

# Commerce
W("backend/commerce/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from business.models import Business
from crm.models import Customer

class Product(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="products")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, default="physical")  # physical, service, rental
    default_price = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="XOF")
    is_active = models.BooleanField(default=True)

class Variant(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="variants")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=120, unique=True)
    price = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

class Cart(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="carts")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=16, default="open")

class CartItem(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="cart_items")
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    qty = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=18, decimal_places=2)

class Order(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="orders")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="orders")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default="pending")
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="XOF")

class OrderItem(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="order_items")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    qty = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=18, decimal_places=2)

class Review(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(default=5)
    comment = models.TextField(blank=True, null=True)
""")

# Payments
W("backend/payments/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from commerce.models import Order

class GatewayAccount(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="gateway_accounts")
    kind = models.CharField(max_length=20)  # card, paypal, mtn_momo, orange_money, flooz, tmoney
    config = models.JSONField(default=dict)

class Payment(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="payments")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="XOF")
    status = models.CharField(max_length=20, default="initiated")  # initiated, succeeded, failed
    provider = models.CharField(max_length=40, default="card")
    provider_ref = models.CharField(max_length=120, blank=True, null=True)
    meta_json = models.JSONField(default=dict, blank=True)

class Refund(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="refunds")
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="refunds")
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, default="pending")

class Payout(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="payouts")
    gateway_account = models.ForeignKey(GatewayAccount, on_delete=models.CASCADE, related_name="payouts")
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, default="pending")
""")

# Inventory
W("backend/inventory/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from business.models import Store
from commerce.models import Variant

class Warehouse(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="warehouses")
    store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)

class StockItem(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="stock_items")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stock_items")
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    qty_on_hand = models.IntegerField(default=0)

class StockLedger(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="stock_ledgers")
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    qty_delta = models.IntegerField()
    reason = models.CharField(max_length=64, default="adjustment")
""")

# Shipments
W("backend/shipments/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from business.models import Address
from commerce.models import Order

class PickupCenter(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="pickup_centers")
    code = models.CharField(max_length=16)
    name = models.CharField(max_length=200)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)

class Shipment(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="shipments")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="shipments")
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    pickup_center = models.ForeignKey(PickupCenter, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default="pending")
    tracking = models.CharField(max_length=64, blank=True, null=True)
""")

# HR
W("backend/hr/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from business.models import Business, Store

class Employee(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="employees")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="employees")
    store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
    status = models.CharField(max_length=20, default="active")
""")

# Invoicing
W("backend/invoicing/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from commerce.models import Order

class TaxRate(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tax_rates")
    country = models.CharField(max_length=2, default="TG")
    name = models.CharField(max_length=80)
    rate = models.DecimalField(max_digits=6, decimal_places=4)

class Invoice(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="invoices")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="invoices")
    number = models.CharField(max_length=50)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="XOF")
    status = models.CharField(max_length=20, default="open")
    pdf_url = models.URLField(blank=True, null=True)
""")

# Appointments
W("backend/appointments/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from crm.models import Customer

class Resource(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="resources")
    type = models.CharField(max_length=20, default="staff")
    name = models.CharField(max_length=200)

class Booking(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="bookings")
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="bookings")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="bookings")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(max_length=20, default="booked")
""")

# Notifications
W("backend/notificationsapp/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant

class NotificationTemplate(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="notif_templates")
    template_key = models.CharField(max_length=120)
    locale = models.CharField(max_length=10, default="en")
    channel = models.CharField(max_length=16, default="email")
    subject = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField()
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)

class NotificationPreference(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="notif_prefs")
    user_id = models.UUIDField()
    channel = models.CharField(max_length=16, default="email")
    is_enabled = models.BooleanField(default=True)
    quiet_hours_json = models.JSONField(blank=True, null=True)

class NotificationDispatch(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="notif_dispatches")
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    to_user_id = models.UUIDField(blank=True, null=True)
    to_address = models.CharField(max_length=255, blank=True, null=True)
    channel = models.CharField(maxlength=16, default="email")
    payload_json = models.JSONField(default=dict)
    status = models.CharField(max_length=16, default="queued")
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)

class NotificationLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="notif_logs")
    dispatch = models.ForeignKey(NotificationDispatch, on_delete=models.CASCADE, related_name="logs")
    provider = models.CharField(max_length=120)
    provider_ref = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=16, default="sent")
    meta_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
""".replace("maxlength", "max_length"))

# Support
W("backend/support/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from crm.models import Customer

class Ticket(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tickets")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=16, default="open")
    priority = models.CharField(max_length=16, default="medium")

class KBArticle(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="kb_articles")
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_published = models.BooleanField(default=False)
""")

# Marketing
W("backend/marketing/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant

class Segment(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="segments")
    name = models.CharField(max_length=200)
    definition_json = models.JSONField(default=dict)

class Campaign(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField(max_length=200)
    channel = models.CharField(max_length=16, default="email")
    content = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=16, default="draft")
""")

# Analytics/CDP
W("backend/analyticsapp/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from crm.models import Customer

class CdpProfile(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="cdp_profiles")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    traits_json = models.JSONField(default=dict)

class Event(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="events")
    profile = models.ForeignKey(CdpProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    name = models.CharField(max_length=120)
    ts = models.DateTimeField(auto_now_add=True)
    props = models.JSONField(default=dict)
""")

# AI
W("backend/aiapp/models.py", """
from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from crm.models import Customer

class AiModel(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=120)
    version = models.CharField(max_length=40)
    task = models.CharField(max_length=32)  # fraud, recommendation, forecast, nlp
    params_json = models.JSONField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

class AiJob(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    model = models.ForeignKey(AiModel, on_delete=models.CASCADE)
    job_type = models.CharField(max_length=16)  # train, infer, batch_infer
    entity_type = models.CharField(max_length=80, blank=True, null=True)
    entity_id = models.UUIDField(blank=True, null=True)
    status = models.CharField(max_length=16, default="queued")
    input_json = models.JSONField(blank=True, null=True)
    output_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class AiPrediction(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    model = models.ForeignKey(AiModel, on_delete=models.CASCADE)
    entity_type = models.CharField(max_length=80)
    entity_id = models.UUIDField()
    score = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    explain_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class AiRecommendation(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    model = models.ForeignKey(AiModel, on_delete=models.SET_NULL, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    context = models.CharField(max_length=80)
    items_json = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
""")

# ---- serializers, viewsets, urls for each app (generic CRUD) ----
APPS = [
 ("platformapp", ["Tenant","Role","UserRole"]),
 ("identity", ["ApiClient","OAuthProvider"]),
 ("taxonomy", ["Industry","Category","Subcategory"]),
 ("business", ["Address","Business","Store"]),
 ("crm", ["Customer","Contact","Pipeline","Opportunity","Activity"]),
 ("commerce", ["Product","Variant","Cart","CartItem","Order","OrderItem","Review"]),
 ("payments", ["GatewayAccount","Payment","Refund","Payout"]),
 ("inventory", ["Warehouse","StockItem","StockLedger"]),
 ("shipments", ["PickupCenter","Shipment"]),
 ("hr", ["Employee"]),
 ("invoicing", ["TaxRate","Invoice"]),
 ("appointments", ["Resource","Booking"]),
 ("notificationsapp", ["NotificationTemplate","NotificationPreference","NotificationDispatch","NotificationLog"]),
 ("support", ["Ticket","KBArticle"]),
 ("marketing", ["Segment","Campaign"]),
 ("analyticsapp", ["CdpProfile","Event"]),
 ("aiapp", ["AiModel","AiJob","AiPrediction","AiRecommendation"]),
]

for app, models in APPS:
    # serializers
    s = ["from rest_framework import serializers", f"from .models import {', '.join(models)}", ""]
    for m in models:
        s.append(f"class {m}Serializer(serializers.ModelSerializer):\n    class Meta:\n        model = {m}\n        fields = '__all__'\n")
    W(f"backend/{app}/serializers.py", "\n".join(s))

    # views
    v = ["from rest_framework import viewsets", f"from .models import {', '.join(models)}", f"from .serializers import {', '.join(m+'Serializer' for m in models)}", ""]
    for m in models:
        v.append(f"class {m}ViewSet(viewsets.ModelViewSet):\n    queryset = {m}.objects.all().order_by('-id') if hasattr({m}, 'id') else {m}.objects.all()\n    serializer_class = {m}Serializer\n")
    W(f"backend/{app}/views.py", "\n".join(v))

    # urls
    u = ["from rest_framework.routers import DefaultRouter","from django.urls import path, include"]
    for m in models:
        u.append(f"from .views import {m}ViewSet")
    u.append("\nrouter = DefaultRouter()")
    for m in models:
        u.append(f"router.register(r'{m.lower()}', {m}ViewSet)")
    u.append("\nurlpatterns = [ path('', include(router.urls)) ]")
    W(f"backend/{app}/urls.py", "\n".join(u))

# Hook up root URL for docs/healthz + all apps (idempotent overwrite)
W("backend/vendora_backend/urls.py", """
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

def root(_r): 
    return JsonResponse({"service":"vendora-backend","docs":"/api/docs","health":"/api/v1/core/healthz"})

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

# Minimal identity/urls.py so include doesn't 404
W("backend/identity/urls.py", "from django.urls import path, include\nfrom rest_framework.routers import DefaultRouter\nrouter=DefaultRouter()\nurlpatterns=[path('', include(router.urls))]\n")

# ------------------------------------------------------------
# Frontend – wire API helper & simple module pages
# ------------------------------------------------------------
W("frontend/lib/api.ts", """
const base = process.env.NEXT_PUBLIC_API_BASE || '';
export async function api(path: string, opts: RequestInit = {}) {
  const res = await fetch(base + path, { ...opts, headers: { 'Content-Type': 'application/json', ...(opts.headers||{}) } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}
""")

# Simple overview pages per module (links only; expand later)
modules = ["crm","commerce","inventory","shipments","marketing","support","invoicing","appointments","notifications","analytics","ai","settings"]
for m in modules:
    W(f"frontend/app/{m}/page.tsx", f"""
import Link from 'next/link';
export default async function Page() {{
  return (<div>
    <h1>{m.upper()}</h1>
    <p>Module shell. Backend API at {{process.env.NEXT_PUBLIC_API_BASE}}.</p>
    <ul>
      <li><Link href="/">Home</Link></li>
    </ul>
  </div>);
}}
""")

print("OK - Full structure generated.")
PY
