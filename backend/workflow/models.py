from django.db import models
from common.models import BaseModel

class Workflow(BaseModel):
    tenant = models.ForeignKey(
    "platformapp.Tenant",
    on_delete=models.CASCADE,
    related_name="workflow_events",
    related_query_name="workflow_event",
    )

    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    trigger = models.CharField(max_length=80)        # e.g., order.created
    condition_json = models.JSONField(default=dict)  # optional DSL
    actions_json = models.JSONField(default=list)    # e.g., [{"action":"create_invoice"}, {"action":"notify","channel":"email"}]

class Event(BaseModel):
    tenant = models.ForeignKey(
        "platformapp.Tenant",
        on_delete=models.CASCADE,
        related_name="workflow_engine_events",
        related_query_name="workflow_engine_event",
    )
    name = models.CharField(max_length=80)           # order.created
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, default="queued")  # queued|processing|done|error
    error = models.TextField(blank=True, null=True)

class WorkflowRun(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="workflow_runs")
    workflow = models.ForeignKey("workflow.Workflow", on_delete=models.CASCADE, related_name="runs")
    event = models.ForeignKey("workflow.Event", on_delete=models.CASCADE, related_name="runs")
    status = models.CharField(max_length=16, default="processing")  # processing|done|error
    log = models.TextField(blank=True, null=True)
