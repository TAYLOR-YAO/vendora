from django.db import models
from django.utils import timezone
from common.models import BaseModel


class FeatureFlag(BaseModel):
    """
    Simple server-side flags. Enforced in app code / views.
    Examples: checkout_v2, fraud_ml, marketing_beta
    """
    key = models.SlugField(max_length=64, unique=True)
    enabled = models.BooleanField(default=False)
    audience = models.CharField(max_length=32, blank=True, null=True)  # e.g. "all", "internal", "beta"
    meta_json = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.key}={self.enabled}"


class PublicConfig(BaseModel):
    """
    Public configuration consumable by the frontend (safe to expose).
    Examples: default_currency, support_email, countries_enabled
    """
    key = models.SlugField(max_length=64, unique=True)
    value_json = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.key


class Announcement(BaseModel):
    """
    Time-bound announcements/maintenance banners for UI.
    """
    level = models.CharField(max_length=16, default="info")  # info|warning|critical
    title = models.CharField(max_length=200)
    body = models.TextField()
    starts_at = models.DateTimeField(blank=True, null=True)
    ends_at = models.DateTimeField(blank=True, null=True)
    is_published = models.BooleanField(default=False)

    @property
    def is_active(self):
        now = timezone.now()
        if not self.is_published:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True

    def __str__(self):
        return f"[{self.level}] {self.title}"
