from django.db import models
from django.utils import timezone
from common.models import BaseModel


class Customer(BaseModel):
    """
    B2C/B2B customer record (private). Use public LeadIntake to create customers anonymously.
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="customers")

    # identity
    type = models.CharField(max_length=20, default="person")  # person|company
    name = models.CharField(max_length=200)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name  = models.CharField(max_length=100, blank=True, null=True)
    company    = models.CharField(max_length=200, blank=True, null=True)

    # contact
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)

    # marketing & lifecycle
    status = models.CharField(max_length=24, default="active")  # active|inactive|blocked
    source = models.CharField(max_length=50, blank=True, null=True)  # webform, import, pos, api
    tags   = models.JSONField(default=list, blank=True)  # ["vip","newsletter"]

    # privacy
    marketing_consent = models.BooleanField(default=False)
    consent_ts = models.DateTimeField(blank=True, null=True)

    # extras
    meta_json = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "email"]),
            models.Index(fields=["tenant", "phone"]),
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "-created_at"]),
        ]
        constraints = [
            # Not strictly unique because same email can occur in multiple tenants
            # but you can enforce uniqueness within tenant if you want:
            # models.UniqueConstraint(fields=["tenant", "email"], name="uniq_customer_email_per_tenant"),
        ]


class Contact(BaseModel):
    """
    Individual contact (often linked to a Customer account). Private.
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="contacts")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, blank=True, null=True, related_name="contacts")

    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name  = models.CharField(max_length=100, blank=True, null=True)
    email      = models.EmailField(blank=True, null=True)
    phone      = models.CharField(max_length=32, blank=True, null=True)
    title      = models.CharField(max_length=120, blank=True, null=True)

    is_primary = models.BooleanField(default=False)
    meta_json  = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "customer"]),
            models.Index(fields=["tenant", "email"]),
            models.Index(fields=["tenant", "is_primary"]),
        ]


class Pipeline(BaseModel):
    """
    Sales pipeline. Private.
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="pipelines")
    name = models.CharField(max_length=120)
    is_default = models.BooleanField(default=False)
    stages = models.JSONField(default=list, blank=True)  # ["new","qualified","proposal","won","lost"]

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "is_default"]),
            models.Index(fields=["tenant", "name"]),
        ]


class Opportunity(BaseModel):
    """
    Deal / opportunity. Private.
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="opportunities")
    pipeline = models.ForeignKey("crm.Pipeline", on_delete=models.SET_NULL, null=True, blank=True)
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="opportunities")

    name   = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="XOF")
    stage  = models.CharField(max_length=32, default="new")
    probability = models.PositiveIntegerField(default=0)  # 0..100
    expected_close = models.DateField(blank=True, null=True)

    owner_user_id = models.UUIDField(blank=True, null=True)
    source = models.CharField(max_length=50, blank=True, null=True)
    tags   = models.JSONField(default=list, blank=True)
    meta_json = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "stage"]),
            models.Index(fields=["tenant", "owner_user_id"]),
            models.Index(fields=["tenant", "-created_at"]),
        ]


class Activity(BaseModel):
    """
    Note, call, meeting, task. Private.
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="activities")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="activities")
    opportunity = models.ForeignKey("crm.Opportunity", on_delete=models.SET_NULL, null=True, blank=True, related_name="activities")

    kind = models.CharField(max_length=20, default="note")  # note|call|meeting|task|email
    direction = models.CharField(max_length=8, blank=True, null=True)  # in|out (for calls/emails)
    content = models.TextField(blank=True, null=True)
    due_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    actor_user_id = models.UUIDField(blank=True, null=True)

    attachments = models.JSONField(default=list, blank=True)  # [{"name":"...", "url":"..."}]
    meta_json   = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "kind"]),
            models.Index(fields=["tenant", "due_at"]),
            models.Index(fields=["tenant", "completed_at"]),
        ]
