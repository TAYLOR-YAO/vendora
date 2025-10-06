from __future__ import annotations
from celery import shared_task
from collections import defaultdict, deque
from datetime import timedelta, datetime, timezone

from django.db import transaction
from django.db.models import F

from .models import Event, CoVisitEdge, ItemStat
from platformapp.models import Tenant

def _decay_weight(age_hours: float) -> float:
    # 24h half-life ~ exp(-ln(2)*age/24)
    import math
    return math.exp(-0.028877 * age_hours)

@shared_task
def rebuild_covisitation(tenant_id: str, window_days: int = 30, max_session_gap_min: int = 30):
    """
    Build co-visitation edges from 'view'/'product_view' events:
    sliding session window per profile, within max_session_gap.
    """
    tenant = Tenant.objects.get(id=tenant_id)
    since = datetime.now(timezone.utc) - timedelta(days=window_days)

    qs = (Event.objects
          .filter(tenant=tenant, name__in=["product_view","view"], ts__gte=since)
          .order_by("profile_id","ts")
          .values("profile_id","ts","props"))
    # Sessionize + collect pairs per profile
    pair_weights = defaultdict(float)
    prev_ts = None
    prev_items = deque([], maxlen=5)  # small context window
    prev_profile = None

    for row in qs.iterator(chunk_size=5000):
        pid, ts, props = row["profile_id"], row["ts"], row["props"] or {}
        item = str(props.get("product_id") or props.get("item_id") or "")
        if not item:
            continue

        if (prev_profile != pid) or (prev_ts and (ts - prev_ts).total_seconds() > max_session_gap_min*60):
            prev_items.clear()

        # co-visit with items in window
        for other in list(prev_items):
            if other == item:
                continue
            a, b = sorted([item, other])
            age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0
            w = _decay_weight(age_h)
            pair_weights[(a,b)] += w

        prev_items.appendleft(item)
        prev_ts = ts; prev_profile = pid

    with transaction.atomic():
        for (a,b), w in pair_weights.items():
            obj, _ = CoVisitEdge.objects.get_or_create(tenant=tenant, item_a=a, item_b=b, defaults={"weight": 0.0})
            obj.weight = float(obj.weight) + float(w)
            obj.save(update_fields=["weight","updated_at"])

@shared_task
def rebuild_popularity(tenant_id: str, window_days: int = 30):
    tenant = Tenant.objects.get(id=tenant_id)
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    counts = defaultdict(float)

    qs = Event.objects.filter(tenant=tenant, name__in=["product_view","purchase","add_to_cart"], ts__gte=since).values("ts","props")
    for row in qs.iterator(chunk_size=5000):
        ts, props = row["ts"], row["props"] or {}
        item = str(props.get("product_id") or props.get("item_id") or "")
        if not item:
            continue
        age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0
        base = 3.0 if props.get("name") == "purchase" else 1.0
        counts[item] += base * _decay_weight(age_h)

    with transaction.atomic():
        for item, score in counts.items():
            obj, _ = ItemStat.objects.get_or_create(tenant=tenant, item_id=item, defaults={"popularity":0})
            obj.popularity = float(score)
            obj.last_event_at = datetime.now(timezone.utc)
            obj.save(update_fields=["popularity","last_event_at","updated_at"])
