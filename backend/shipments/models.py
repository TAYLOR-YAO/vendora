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
