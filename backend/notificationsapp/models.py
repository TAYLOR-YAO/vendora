from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant

class NotificationTemplate(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="notif_templates")
    template_key = models.CharField(max_length=120)
    locale = models.CharField(max_length=10, default="en")
    channel = models.CharField(max_length=16, default="email")
    subject = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField()
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)

class NotificationPreference(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="notif_prefs")
    user_id = models.UUIDField()
    channel = models.CharField(max_length=16, default="email")
    is_enabled = models.BooleanField(default=True)
    quiet_hours_json = models.JSONField(blank=True, null=True)

class NotificationDispatch(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="notif_dispatches")
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    to_user_id = models.UUIDField(blank=True, null=True)
    to_address = models.CharField(max_length=255, blank=True, null=True)
    channel = models.CharField(max_length=16, default="email")
    payload_json = models.JSONField(default=dict)
    status = models.CharField(max_length=16, default="queued")
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)

class NotificationLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="notif_logs")
    dispatch = models.ForeignKey(NotificationDispatch, on_delete=models.CASCADE, related_name="logs")
    provider = models.CharField(max_length=120)
    provider_ref = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=16, default="sent")
    meta_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
