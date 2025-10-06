from __future__ import annotations
from typing import Dict, Any
from django.utils import timezone
from platformapp.models import Tenant
from .models import CdpProfile, Event

def resolve_profile_for_ingest(tenant: Tenant, payload: Dict[str, Any]) -> CdpProfile | None:
    """
    Resolve or create a CDP profile for ingestion:
      - Prefer hashed identifiers in traits
      - Fall back to device_id / user_id
    """
    traits = payload.get("traits") or {}
    email_hash = traits.get("email_hash")
    phone_hash = traits.get("phone_hash")
    device_id = payload.get("device_id")
    user_id = payload.get("user_id")

    qs = CdpProfile.objects.filter(tenant=tenant)
    prof = None
    if email_hash:
        prof = qs.filter(traits_json__email_hash=email_hash).first()
    if not prof and phone_hash:
        prof = qs.filter(traits_json__phone_hash=phone_hash).first()
    if not prof and user_id:
        prof = qs.filter(traits_json__user_id=user_id).first()
    if not prof and device_id:
        prof = qs.filter(traits_json__device_id=device_id).first()

    if not prof:
        prof = CdpProfile.objects.create(
            tenant=tenant,
            traits_json={
                "email_hash": email_hash,
                "phone_hash": phone_hash,
                "user_id": user_id,
                "device_id": device_id,
            },
        )
    return prof
