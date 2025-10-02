from django.db import models
from common.models import BaseModel
from platformapp.models import Tenant
from crm.models import Customer

class AiModel(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=120)
    version = models.CharField(max_length=40)
    task = models.CharField(max_length=32)  # fraud, recommendation, forecast, nlp
    params_json = models.JSONField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

class AiJob(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    model = models.ForeignKey(AiModel, on_delete=models.CASCADE)
    job_type = models.CharField(max_length=16)  # train, infer, batch_infer
    entity_type = models.CharField(max_length=80, blank=True, null=True)
    entity_id = models.UUIDField(blank=True, null=True)
    status = models.CharField(max_length=16, default="queued")
    input_json = models.JSONField(blank=True, null=True)
    output_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class AiPrediction(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    model = models.ForeignKey(AiModel, on_delete=models.CASCADE)
    entity_type = models.CharField(max_length=80)
    entity_id = models.UUIDField()
    score = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    explain_json = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class AiRecommendation(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    model = models.ForeignKey(AiModel, on_delete=models.SET_NULL, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    context = models.CharField(max_length=80)
    items_json = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
