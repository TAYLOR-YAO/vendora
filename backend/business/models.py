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
