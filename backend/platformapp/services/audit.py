from __future__ import annotations
from typing import Optional, Dict, Any
from django.utils import timezone
from platformapp.models import AuditLog, Tenant

REDACT_KEYS = {"password", "token", "access", "refresh", "card", "cvv", "pin"}

def _sanitize(meta: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in (meta or {}).items():
        if k.lower() in REDACT_KEYS:
            out[k] = "***"
        else:
            out[k] = v
    return out

def log_event(*, tenant: Tenant, user_id: Optional[str], action: str,
              entity: str, entity_id: str, meta: Optional[Dict[str, Any]] = None) -> None:
    AuditLog.objects.create(
        tenant=tenant,
        user_id=user_id,
        action=action[:80],
        entity=entity[:120],
        entity_id=str(entity_id)[:120],
        meta_json=_sanitize(meta or {}),
        created_at=timezone.now(),
    )
