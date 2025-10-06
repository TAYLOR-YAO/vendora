from __future__ import annotations
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.utils import timezone
from common.models import BaseModel

# A person/device profile in your CDP
class CdpProfile(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="cdp_profiles")
    customer = models.ForeignKey("crm.Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="cdp_profiles")

    # Traits should be PII-safe; raw emails/phones should be hashed before save (see serializer)
    traits_json = models.JSONField(default=dict, blank=True)

    # Optional for fast text search (e.g., name, phone last 4)
    search = SearchVectorField(null=True, blank=True)

    class Meta:
        indexes = [
            GinIndex(fields=["traits_json"]),
            GinIndex(fields=["search"]),
            models.Index(fields=["tenant", "created_at"]),
        ]


class Event(models.Model):
    """
    Write-heavy table; keep it flat and small. Anything big goes into props.
    """
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(
        "platformapp.Tenant",
        on_delete=models.CASCADE,
        related_name="analytics_events",
        related_query_name="analytics_event",
    )

    # Optional link to a known profile
    profile = models.ForeignKey("analyticsapp.CdpProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="events")

    # Session & device identifiers help with retention and funnels
    session_id = models.CharField(max_length=64, blank=True, null=True)
    device_id = models.CharField(max_length=64, blank=True, null=True)
    user_id = models.CharField(max_length=64, blank=True, null=True)   # external id (hash-uids client-side)
    name = models.CharField(max_length=120)

    # Africa-focused: unreliable clocks—allow client_ts, fall back to server ts
    client_ts = models.DateTimeField(blank=True, null=True)
    ts = models.DateTimeField(default=timezone.now, db_index=True)

    # Geo/network hints from ingestion edge (don’t store raw IPs by default)
    ip_hash = models.CharField(max_length=64, blank=True, null=True)
    country = models.CharField(max_length=2, blank=True, null=True)  # e.g., “TG”, “GH”, …

    props = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            GinIndex(fields=["props"]),
            models.Index(fields=["tenant", "name", "ts"]),
            models.Index(fields=["tenant", "session_id", "ts"]),
        ]

class CoVisitEdge(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="covis_edges")
    item_a = models.CharField(max_length=120, db_index=True)  # product ID/slug
    item_b = models.CharField(max_length=120, db_index=True)
    weight = models.FloatField(default=0.0)  # co-occur strength
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "item_a", "item_b")

class ItemStat(models.Model):
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="item_stats")
    item_id = models.CharField(max_length=120, db_index=True)
    popularity = models.FloatField(default=0.0)   # time-decayed count/score
    last_event_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "item_id")

# --- NEW: RiskSignal (training/serving table for fraud scoring) ---
class RiskSignal(BaseModel):
    """
    One row per transaction (or charge), with features and (optionally) label.
    y_label: 1 = fraud/chargeback/refund, 0 = legitimate; null = unlabeled.
    """
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="risk_signals")

    tx_id = models.CharField(max_length=120)                 # provider or internal transaction id
    user_id = models.UUIDField(null=True, blank=True)
    order_id = models.UUIDField(null=True, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=8, default="XOF")
    channel = models.CharField(max_length=32, default="card")   # card|mobile_money|bank|paypal|...
    country = models.CharField(max_length=4, default="TG")

    features_json = models.JSONField(default=dict, blank=True)  # flattened features used by model
    y_label = models.IntegerField(null=True, blank=True)        # 1,0 or null
    label_source = models.CharField(max_length=32, blank=True, null=True)  # 'auto','manual','chargeback','refund'

    # Optional guardrail fields
    rules_alerts = models.JSONField(default=list, blank=True)   # list of tripped rules
    score = models.FloatField(null=True, blank=True)            # latest model score (0..1)

    class Meta:
        unique_together = (("tenant", "tx_id"),)
        indexes = [
            models.Index(fields=["tenant", "channel"]),
            models.Index(fields=["tenant", "y_label"]),
            models.Index(fields=["tenant", "created_at"]),
        ]


# --- OPTIONAL: Metrics snapshots for model monitoring ---
class ModelMetric(BaseModel):
    tenant = models.ForeignKey("platformapp.Tenant", on_delete=models.CASCADE, related_name="model_metrics")
    model_key = models.CharField(max_length=120)         # e.g., 'lr_v1'
    slice_key = models.CharField(max_length=120)         # e.g., 'last_30d|TG|mobile_money'
    auc = models.FloatField(null=True, blank=True)
    pr_auc = models.FloatField(null=True, blank=True)
    precision_at_90_recall = models.FloatField(null=True, blank=True)
    recall_at_1pct_fpr = models.FloatField(null=True, blank=True)

# ... keep existing imports and models (CdpProfile, Event, RiskSignal, ModelMetric)

class DeviceFingerprint(models.Model):
    """
    A normalized device profile used across providers.
    Useful for velocity checks, linking accounts, and model features.
    """
    id = models.BigAutoField(primary_key=True)
    tenant = models.ForeignKey(
    "platformapp.Tenant",
    on_delete=models.CASCADE,
    related_name="device_fingerprints",
    related_query_name="device_fingerprint",
    )
    device_id = models.CharField(max_length=200)  # e.g., hashed UA+IP+hw, or provider device id
    user_id = models.UUIDField(null=True, blank=True)

    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    # Store any provider raw signal or derived attributes (browser, OS, SIM, IMSI, jailbreak flag, etc.)
    fingerprints_json = models.JSONField(default=dict, blank=True)

    # Optional risk score aggregated from rules/signals (0..1)
    risk_score = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = (("tenant", "device_id"),)
        indexes = [
            models.Index(fields=["tenant", "device_id"]),
            models.Index(fields=["tenant", "user_id"]),
            models.Index(fields=["tenant", "last_seen"]),
        ]

    def __str__(self):
        return f"{self.device_id}"
