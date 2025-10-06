from django.db import models
from django.utils import timezone
from decimal import Decimal
from common.models import BaseModel


class GatewayAccount(BaseModel):
    tenant = models.ForeignKey(
    "platformapp.Tenant",
    on_delete=models.CASCADE,
    related_name="payment_subscriptions",
    related_query_name="payment_subscription",
    )
    kind = models.CharField(max_length=20)  # stripe, paypal, tmoney, mtn, orange, fooz, bank, mock
    config = models.JSONField(default=dict)  # public conf (publishable key, endpoints)
    # NEW
    display_name = models.CharField(max_length=100, blank=True, null=True)
    active = models.BooleanField(default=True)
    default_currency = models.CharField(max_length=3, default="XOF")
    supported_methods = models.JSONField(default=list, blank=True)  # e.g. ["card","mobile_money"]
    region = models.CharField(max_length=50, blank=True, null=True)
    webhook_secret = models.CharField(max_length=200, blank=True, null=True)  # HMAC/shared secret for webhooks
    payout_schedule = models.JSONField(default=dict, blank=True)  # optional config

    class Meta:
        indexes = [models.Index(fields=["tenant", "kind", "active"])]

    def __str__(self):
        return self.display_name or f"{self.kind} ({self.tenant_id})"


class Payment(BaseModel):
    """
    One logical payment against an Order. We keep a minimal intent surface so the app
    works with different providers (card, bank, PayPal, mobile money).
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="payments")
    order = models.ForeignKey("commerce.Order", on_delete=models.CASCADE, related_name="payments")

    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="XOF")

    status = models.CharField(
        max_length=20,
        default="initiated",
        choices=[
            ("initiated", "Initiated"),
            ("requires_action", "Requires Action"),
            ("processing", "Processing"),
            ("succeeded", "Succeeded"),
            ("failed", "Failed"),
            ("canceled", "Canceled"),
            ("refunded", "Refunded"),
            ("partially_refunded", "Partially Refunded"),
        ],
    )
    provider = models.CharField(max_length=40, default="card")           # tmoney|mtn|orange|fooz|card|paypal|bank
    provider_ref = models.CharField(max_length=120, blank=True, null=True)  # provider charge/txn id
    provider_intent_id = models.CharField(max_length=120, blank=True, null=True)  # payment intent/session
    method = models.CharField(max_length=40, default="card")  # card|mobile_money|paypal|bank
    flow = models.CharField(max_length=40, default="server_confirm")     # redirect|server_confirm|collect_on_delivery

    refunded_amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    failure_code = models.CharField(max_length=64, blank=True, null=True)
    failure_message = models.TextField(blank=True, null=True)

    captured_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    meta_json = models.JSONField(default=dict, blank=True)  # idempotency_key, phone, payer_name, etc.

    client_secret = models.CharField(max_length=200, blank=True, null=True)  # if provider uses secrets

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "order", "status"]),
            models.Index(fields=["tenant", "provider", "provider_ref"]),
        ]

    @property
    def is_refundable(self) -> bool:
        return self.status in ("succeeded", "partially_refunded") and self.amount > self.refunded_amount


class Refund(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="refunds")
    payment = models.ForeignKey("payments.Payment", on_delete=models.CASCADE, related_name="refunds")
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(
        max_length=20,
        default="pending",
        choices=[("pending","Pending"),("succeeded","Succeeded"),("failed","Failed"),("canceled","Canceled")],
    )
    # NEW
    reason = models.CharField(max_length=60, blank=True, null=True)
    provider_ref = models.CharField(max_length=120, blank=True, null=True)
    meta_json = models.JSONField(default=dict, blank=True)


class Payout(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="payouts")
    gateway_account = models.ForeignKey("payments.GatewayAccount", on_delete=models.CASCADE, related_name="payouts")
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="XOF")
    status = models.CharField(
        max_length=20,
        default="pending",
        choices=[("pending","Pending"),("processing","Processing"),("paid","Paid"),("failed","Failed"),("canceled","Canceled")],
    )
    destination = models.CharField(max_length=120, blank=True, null=True)  # bank acct/mobile wallet
    meta_json = models.JSONField(default=dict, blank=True)


# ---- Optional additions for installments & subscriptions ----

class InstallmentPlan(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="installment_plans")
    order = models.ForeignKey("commerce.Order", on_delete=models.CASCADE, related_name="installment_plans")
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="XOF")
    schedule = models.JSONField(default=list, blank=True)  # [{"due_date": "...", "amount": "100.00", "status": "pending"}]
    status = models.CharField(
        max_length=20,
        default="active",
        choices=[("active","Active"),("completed","Completed"),("canceled","Canceled"),("defaulted","Defaulted")],
    )
    meta_json = models.JSONField(default=dict, blank=True)


class Subscription(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="subscriptions")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True)
    plan_code = models.CharField(max_length=64)  # your pricing plan id
    status = models.CharField(
        max_length=20,
        default="active",
        choices=[("trial","Trial"),("active","Active"),("past_due","Past Due"),("canceled","Canceled")],
    )
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField(blank=True, null=True)
    cancel_at = models.DateTimeField(blank=True, null=True)
    currency = models.CharField(max_length=3, default="XOF")
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    gateway_account = models.ForeignKey("payments.GatewayAccount", on_delete=models.SET_NULL, null=True, blank=True)
    meta_json = models.JSONField(default=dict, blank=True)


class ProviderEvent(BaseModel):
    """
    Raw webhook log (for audits/debugging).
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="provider_events")
    gateway_account = models.ForeignKey("payments.GatewayAccount", on_delete=models.SET_NULL, null=True, blank=True)
    provider = models.CharField(max_length=40)
    event_type = models.CharField(max_length=80)
    payload = models.JSONField(default=dict, blank=True)
    signature = models.CharField(max_length=200, blank=True, null=True)
