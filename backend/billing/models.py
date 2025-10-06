from django.db import models
from common.models import BaseModel

class Plan(BaseModel):
    tenant = models.ForeignKey(
    "platformapp.Tenant",
    on_delete=models.CASCADE,
    related_name="billing_plans",
    related_query_name="billing_plan",   # <- prevents reverse query name 'plan'
    )
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    billing_cycle = models.CharField(max_length=16, default="monthly")  # monthly|yearly
    features_json = models.JSONField(default=dict)  # limits, entitlements

class Price(BaseModel):
    plan = models.ForeignKey("billing.Plan", on_delete=models.CASCADE, related_name="prices")
    currency = models.CharField(max_length=3, default="XOF")
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # per seat or per unit
    mode = models.CharField(max_length=16, default="per_seat")     # per_seat|usage

class Subscription(BaseModel):
    tenant = models.ForeignKey(
    "platformapp.Tenant",
    on_delete=models.CASCADE,
    related_name="billing_subscriptions",
    related_query_name="billing_subscription",
    )
    plan = models.ForeignKey("billing.Plan", on_delete=models.PROTECT)
    status = models.CharField(max_length=20, default="active")      # active|past_due|canceled
    seats = models.IntegerField(default=1)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()

class UsageRecord(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="usage_records")
    metric = models.CharField(max_length=50)       # e.g. "api_calls", "records_indexed"
    quantity = models.IntegerField(default=0)
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
