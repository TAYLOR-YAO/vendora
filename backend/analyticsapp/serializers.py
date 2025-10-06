from __future__ import annotations
from rest_framework import serializers
from django.utils.crypto import salted_hmac
from .models import CdpProfile, Event, RiskSignal, ModelMetric, DeviceFingerprint

def _stable_hash(tenant_id: str, value: str) -> str:
    """PII hashing helper (stable per-tenant)."""
    if not value:
        return ""
    return salted_hmac(str(tenant_id), value).hexdigest()

class CdpProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CdpProfile
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")

    def validate_traits_json(self, traits):
        # Hash common PII keys if passed raw
        tenant_id = self.instance.tenant_id if self.instance else self.initial_data.get("tenant")
        if not tenant_id:
            return traits
        pii_keys = ["email", "phone", "ip"]
        hashed = dict(traits or {})
        for k in pii_keys:
            if k in hashed and hashed[k]:
                hashed[f"{k}_hash"] = _stable_hash(tenant_id, str(hashed[k]).strip().lower())
                # Optionally drop raw values:
                hashed.pop(k, None)
        return hashed


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"

    def validate(self, data):
        # Normalize timestamps
        if not data.get("client_ts"):
            # Frontend didn’t send—fine
            pass
        return data

    def create(self, validated):
        # Auto-hash IP if present in props
        tenant_id = validated["tenant_id"] if "tenant_id" in validated else validated["tenant"].id
        props = dict(validated.get("props") or {})
        ip = props.pop("ip", None)
        if ip:
            validated["ip_hash"] = _stable_hash(tenant_id, ip)
        return super().create(validated)
# NEW
class RiskSignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskSignal
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")


# NEW
class ModelMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelMetric
        fields = "__all__"
        read_only_fields = ("tenant", "created_at", "updated_at")

class DeviceFingerprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceFingerprint
        fields = "__all__"
        read_only_fields = ("tenant", "first_seen", "last_seen")


