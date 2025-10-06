from django.db import models
from django.utils import timezone
from common.models import BaseModel


CHANNEL_CHOICES = (
    ("email", "Email"),
    ("sms", "SMS"),
    ("push", "Push"),
    ("whatsapp", "WhatsApp"),
    ("webhook", "Webhook"),
)

DISPATCH_STATUS = (
    ("queued", "Queued"),
    ("sending", "Sending"),
    ("sent", "Sent"),
    ("failed", "Failed"),
    ("cancelled", "Cancelled"),
)

PREF_SCOPE = (
    ("global", "Global"),
    ("topic", "Topic"),
    ("template", "Template"),
)

DIGEST_PERIOD = (
    ("none", "None"),
    ("hourly", "Hourly"),
    ("daily", "Daily"),
    ("weekly", "Weekly"),
)


class Topic(BaseModel):
    """
    Optional: groups templates under business-relevant topics (orders, billing, marketing).
    Useful for preferences and bulk opt-in/out.
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="notif_topics")
    key = models.CharField(max_length=64)   # e.g. 'orders', 'billing', 'marketing'
    name = models.CharField(max_length=160)

    class Meta:
        unique_together = (("tenant", "key"),)
        indexes = [models.Index(fields=["tenant", "key"])]

    def __str__(self):
        return self.name


class NotificationTemplate(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="notif_templates")
    topic = models.ForeignKey("notificationsapp.Topic", on_delete=models.SET_NULL, null=True, blank=True, related_name="templates")
    template_key = models.CharField(max_length=120)  # stable key (e.g. 'order_paid')
    locale = models.CharField(max_length=10, default="en")
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES, default="email")

    subject = models.CharField(max_length=255, blank=True, null=True)  # email/push title
    body = models.TextField(help_text="Jinja/Django template string with {{variables}}")
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)

    render_hints = models.JSONField(default=dict, blank=True)  # e.g., {"engine": "django", "markdown": True}

    class Meta:
        unique_together = (("tenant", "template_key", "locale", "channel", "version"),)
        indexes = [models.Index(fields=["tenant", "template_key", "locale", "channel"])]

    def __str__(self):
        return f"{self.template_key} ({self.locale}/{self.channel}) v{self.version}"


class NotificationPreference(BaseModel):
    """
    Per-user per-tenant preference. Can be global, by topic, or per-template.
    Quiet hours let users mute alerts overnight; digest options bundle messages.
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="notif_prefs")
    user_id = models.UUIDField()
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES, default="email")
    scope = models.CharField(max_length=16, choices=PREF_SCOPE, default="global")

    topic = models.ForeignKey("notificationsapp.Topic", on_delete=models.SET_NULL, null=True, blank=True)
    template = models.ForeignKey("notificationsapp.NotificationTemplate", on_delete=models.SET_NULL, null=True, blank=True)

    is_enabled = models.BooleanField(default=True)
    quiet_hours_json = models.JSONField(blank=True, null=True)  # {"start":"22:00","end":"07:00","tz":"Africa/Lome"}
    digest = models.CharField(max_length=16, choices=DIGEST_PERIOD, default="none")

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "user_id", "channel", "scope"]),
        ]


class NotificationDispatch(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="notif_dispatches")

    template = models.ForeignKey("notificationsapp.NotificationTemplate", on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey("notificationsapp.Topic", on_delete=models.SET_NULL, null=True, blank=True)

    to_user_id = models.UUIDField(blank=True, null=True)
    to_address = models.CharField(max_length=255, blank=True, null=True)
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES, default="email")

    payload_json = models.JSONField(default=dict)
    attachments = models.JSONField(default=list, blank=True)  # [{"url": "...", "filename":"..."}]

    schedule_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=16, choices=DISPATCH_STATUS, default="queued")
    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    provider_ref = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "channel", "status"]),
            models.Index(fields=["tenant", "created_at"]),
        ]


class NotificationLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="notif_logs")
    dispatch = models.ForeignKey("notificationsapp.NotificationDispatch", on_delete=models.CASCADE, related_name="logs")

    provider = models.CharField(max_length=120)  # e.g. 'sendgrid', 'twilio', 'expo', 'webhook'
    provider_ref = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=16, default="sent")
    meta_json = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
