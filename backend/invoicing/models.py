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
