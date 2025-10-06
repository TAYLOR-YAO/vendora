from django.db import models
from common.models import BaseModel

class Tenant(BaseModel):
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, default="active")
    plan = models.CharField(max_length=20, default="free")
    region = models.CharField(max_length=50, blank=True, null=True)

class Role(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="roles")
    name = models.CharField(max_length=100)
    scope_level = models.CharField(max_length=20, default="business")

class UserRole(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="user_roles")
    user_id = models.UUIDField()
    role = models.ForeignKey("platformapp.Role", on_delete=models.CASCADE)
    business_id = models.UUIDField(blank=True, null=True)
    store_id = models.UUIDField(blank=True, null=True)

# platformapp/models.py (you already have this; keep it central)
class AuditLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="audit_logs")
    user_id = models.UUIDField(blank=True, null=True)
    action = models.CharField(max_length=80)          # e.g. "order.created"
    entity = models.CharField(max_length=120)         # e.g. "commerce.Order"
    entity_id = models.CharField(max_length=120)
    meta_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

