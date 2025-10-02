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
