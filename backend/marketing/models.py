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
