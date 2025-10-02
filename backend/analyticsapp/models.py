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
