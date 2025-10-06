from django.db import models
from django.utils import timezone
from common.models import BaseModel


CHANNEL_CHOICES = (
    ("email", "Email"),
    ("sms", "SMS"),
    ("push", "Push"),
    ("inapp", "In-App"),
    ("whatsapp", "WhatsApp"),
)

CAMPAIGN_STATUS = (
    ("draft", "Draft"),
    ("scheduled", "Scheduled"),
    ("sending", "Sending"),
    ("paused", "Paused"),
    ("completed", "Completed"),
    ("cancelled", "Cancelled"),
)

VARIANT_KIND = (
    ("subject", "Subject"),
    ("content", "Content"),
)


class Segment(BaseModel):
    """
    A dynamic audience definition. definition_json is a simple DSL you control.
    Example:
      {
        "all": [
          {"field":"customer__email__isnull","op":"eq","value":false},
          {"field":"customer__created_at","op":"gte","value":"2025-01-01"}
        ]
      }
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="segments")
    name = models.CharField(max_length=200)
    definition_json = models.JSONField(default=dict, blank=True)

    # Materialization hints
    last_refreshed_at = models.DateTimeField(blank=True, null=True)
    approx_count = models.IntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["tenant", "name"])]

    def __str__(self):
        return self.name


class Campaign(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField(max_length=200)
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES, default="email")
    status = models.CharField(max_length=16, choices=CAMPAIGN_STATUS, default="draft")

    # Targeting
    segment = models.ForeignKey("marketing.Segment", on_delete=models.SET_NULL, null=True, blank=True, related_name="campaigns")
    include_tags = models.JSONField(default=list, blank=True)  # e.g. ["vip","beta"]
    exclude_tags = models.JSONField(default=list, blank=True)

    # Message (for email/sms/push); variants live in CampaignVariant
    subject = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField(blank=True, null=True)  # fallback/default content

    # From/Reply info (email)
    from_name = models.CharField(max_length=120, blank=True, null=True)
    from_address = models.EmailField(blank=True, null=True)
    reply_to = models.EmailField(blank=True, null=True)

    # UTM
    utm_source = models.CharField(max_length=60, blank=True, null=True)
    utm_medium = models.CharField(max_length=60, blank=True, null=True)
    utm_campaign = models.CharField(max_length=60, blank=True, null=True)

    # Scheduling/throttle
    scheduled_at = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    throttle_per_min = models.IntegerField(default=0)  # 0 = unlimited (provider limits still apply)

    # AB split (0.0–1.0 of audience goes to variant A; remainder to B; 0 → disable AB)
    ab_split = models.FloatField(default=0.0)

    class Meta:
        indexes = [models.Index(fields=["tenant", "status", "scheduled_at", "created_at"])]

    def __str__(self):
        return self.name


class CampaignVariant(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="campaign_variants")
    campaign = models.ForeignKey("marketing.Campaign", on_delete=models.CASCADE, related_name="variants")
    kind = models.CharField(max_length=16, choices=VARIANT_KIND, default="content")
    key = models.CharField(max_length=32, default="A")  # "A" or "B" (or more if you extend)
    subject = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["tenant", "campaign", "key"])]
        unique_together = (("campaign", "key"),)


class CampaignSend(BaseModel):
    """
    A single recipient send record (fan-out). You can create these in batches when "sending".
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="campaign_sends")
    campaign = models.ForeignKey("marketing.Campaign", on_delete=models.CASCADE, related_name="sends")
    variant_key = models.CharField(max_length=8, default="A")
    to_user_id = models.UUIDField(blank=True, null=True)
    to_address = models.CharField(max_length=255, blank=True, null=True)  # email or phone
    status = models.CharField(max_length=16, default="queued")  # queued|sent|failed
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    provider_ref = models.CharField(max_length=200, blank=True, null=True)

    # basic metrics
    opens = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    unsubscribed = models.BooleanField(default=False)
    bounced = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["tenant", "campaign", "status", "to_address"])]


class CampaignEvent(models.Model):
    """
    Provider -> webhook -> you -> this table (for analytics).
    """
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="campaign_events")
    campaign = models.ForeignKey("marketing.Campaign", on_delete=models.CASCADE, related_name="events")
    send = models.ForeignKey("marketing.CampaignSend", on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    event = models.CharField(max_length=24)  # delivered|open|click|bounce|spam|unsubscribe
    meta_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["tenant", "campaign", "event", "created_at"])]
