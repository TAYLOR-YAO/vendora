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
