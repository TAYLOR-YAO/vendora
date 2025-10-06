from __future__ import annotations
from django.db import models
from django.utils import timezone
from common.models import BaseModel

class AiModel(BaseModel):
    class AiTask(models.TextChoices):
        FRAUD = "fraud", "Fraud Detection"
        RECOMMENDATION = "recommendation", "Recommendation"
        FORECAST = "forecast", "Forecast"
        NLP = "nlp", "Natural Language Processing"

    class ProviderKind(models.TextChoices):
        LOCAL = "local", "Local/Embedded"
        HTTP = "http", "Remote HTTP"
        SKLEARN = "sklearn", "Scikit-Learn (local)"
        DUMMY = "dummy", "Dummy (rules/random)"

    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_models")
    name = models.CharField(max_length=120)
    version = models.CharField(max_length=40, default="1")
    task = models.CharField(max_length=32, choices=AiTask.choices)
    provider = models.CharField(max_length=24, choices=ProviderKind.choices, default=ProviderKind.DUMMY)

    # For HTTP providers
    endpoint_url = models.URLField(blank=True, null=True)
    auth_token = models.CharField(max_length=255, blank=True, null=True)

    params_json = models.JSONField(blank=True, null=True, help_text="Hyperparams/config per provider")
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=24, default="ready")  # ready|training|failed|archived
    metrics_json = models.JSONField(default=dict, blank=True)  # e.g., auc, f1, latency

    def __str__(self):
        scope = self.tenant.slug if self.tenant_id else "global"
        return f"{self.name} v{self.version} [{scope}]"


class AiJob(models.Model):
    class JobType(models.TextChoices):
        TRAIN = "train", "Train"
        INFER = "infer", "Infer"
        BATCH_INFER = "batch_infer", "Batch Infer"
        RECOMMEND = "recommend", "Recommend"

    class JobStatus(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="ai_jobs")
    model = models.ForeignKey("aiapp.AiModel", on_delete=models.CASCADE, related_name="jobs")
    job_type = models.CharField(max_length=16, choices=JobType.choices)

    # Optional scoping to a domain object
    entity_type = models.CharField(max_length=80, blank=True, null=True)
    entity_id = models.UUIDField(blank=True, null=True)

    # Execution metadata
    status = models.CharField(max_length=16, choices=JobStatus.choices, default=JobStatus.QUEUED)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # 0..100
    priority = models.IntegerField(default=5)  # 1 high..9 low
    throttle_per_sec = models.IntegerField(default=50)  # soft throttle for batch
    attempts = models.IntegerField(default=0)

    input_json = models.JSONField(blank=True, null=True)
    output_json = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    scheduled_at = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def mark_running(self):
        self.status = self.JobStatus.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_done(self, output=None):
        self.status = self.JobStatus.COMPLETED
        self.output_json = output or {}
        self.progress = 100
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "output_json", "progress", "finished_at"])

    def mark_failed(self, msg=""):
        self.status = self.JobStatus.FAILED
        self.error_message = msg[:2000]
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "error_message", "finished_at"])

    def __str__(self):
        return f"Job#{self.id} {self.job_type} {self.status}"


class AiPrediction(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="ai_predictions")
    model = models.ForeignKey("aiapp.AiModel", on_delete=models.CASCADE, related_name="predictions")
    entity_type = models.CharField(max_length=80)
    entity_id = models.UUIDField()
    label = models.CharField(max_length=64, blank=True, null=True)  # e.g., "fraud"
    score = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    threshold = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    explain_json = models.JSONField(blank=True, null=True)
    features_hash = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AiRecommendation(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="ai_recommendations")
    model = models.ForeignKey("aiapp.AiModel", on_delete=models.SET_NULL, null=True, blank=True, related_name="recommendations")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_recommendations")
    context = models.CharField(max_length=80)  # e.g., "homepage", "cart", "product:<id>"
    algo = models.CharField(max_length=32, default="popular")  # popular|similar|personalized
    items_json = models.JSONField(default=list)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
