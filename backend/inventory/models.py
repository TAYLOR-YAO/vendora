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
