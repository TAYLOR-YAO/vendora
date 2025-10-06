from __future__ import annotations
import math
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from celery import shared_task
from celery.exceptions import Retry
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.db.models import QuerySet

from .models import Campaign, CampaignVariant, CampaignSend
from .utils import resolve_segment_queryset
from notificationsapp.utils import queue_notification


# -------- helpers --------

@dataclass
class BatchPlan:
    size: int
    eta_offset_sec: int  # when to run from "now"
    variant_key: str     # 'A' or 'B' for the batch


def _split_ids_for_ab(ids: List[str], split: float) -> Tuple[List[str], List[str]]:
    """Split a sorted id list into A/B buckets by fraction split [0..1]."""
    split = max(0.0, min(1.0, split or 0.0))
    cut = int(len(ids) * split)
    return ids[:cut], ids[cut:]


def _chunked(seq: List[str], chunk_size: int) -> Iterable[List[str]]:
    for i in range(0, len(seq), chunk_size):
        yield seq[i : i + chunk_size]


def _sec_for_batch(batch_size: int, rate_per_min: int) -> int:
    """
    Convert a desired per-minute throttle into a sleep/delay for this batch size.
    Ex: if rate=600/min and batch=300 -> schedule next batch ~30 seconds later.
    """
    if rate_per_min <= 0:
        return 0
    per_item_sec = 60.0 / float(rate_per_min)
    return int(math.ceil(batch_size * per_item_sec))


# -------- batch worker --------

@shared_task(bind=True, max_retries=5, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=300)
def send_campaign_batch(self, campaign_id: str, user_ids: List[str], variant_key: str) -> int:
    """
    Sends one batch for a campaign (creates CampaignSend rows if needed and queues notifications).
    Retries automatically on failure with exponential backoff.
    Returns number of sends completed in this batch.
    """
    try:
        camp: Campaign = Campaign.objects.select_related("segment").get(id=campaign_id)
    except Campaign.DoesNotExist:
        # Nothing to do; don't retry for missing/removed campaign
        return 0

    # Resolve variants (fallback to campaign content/subject)
    vmap = {v.key.upper(): v for v in camp.variants.filter(is_active=True)}
    var = vmap.get(variant_key) or vmap.get("A")

    subject = (var.subject if var and var.subject else camp.subject) or camp.name
    content = (var.content if var and var.content else camp.content) or ""

    completed = 0

    # We’ll lightly resolve the audience rows we’re about to send to
    # (emails are on CRM Customer)
    qs = resolve_segment_queryset(camp.tenant, camp.segment.definition_json) \
        .filter(id__in=user_ids) \
        .only("id", "email", "name")

    # For idempotence: if a send already exists for a (campaign, to_user_id), we update/reuse.
    for cust in qs:
        try:
            with transaction.atomic():
                send, created = CampaignSend.objects.select_for_update().get_or_create(
                    tenant=camp.tenant,
                    campaign=camp,
                    to_user_id=cust.id,
                    defaults={
                        "variant_key": variant_key,
                        "to_address": cust.email,
                        "status": "queued",
                    },
                )
                # if it exists but was failed/queued -> we attempt again
                if not created and send.status == "sent":
                    continue

                payload = {
                    "subject": subject,
                    "content": content,
                    "utm": {
                        "utm_source": camp.utm_source or "vendora",
                        "utm_medium": camp.utm_medium or camp.channel,
                        "utm_campaign": camp.utm_campaign or camp.name,
                    },
                    "campaign_id": str(camp.id),
                    "send_id": str(send.id),
                }

                # Queue through notification service (provider can be email/sms/push/wa…)
                queue_notification(
                    tenant=camp.tenant,
                    template_id=None,
                    topic_id=None,
                    to_user_id=cust.id,
                    to_address=cust.email,
                    channel=camp.channel,
                    payload=payload,
                )

                send.status = "sent"
                send.sent_at = timezone.now()
                send.save(update_fields=["status", "sent_at"])

                completed += 1
        except Exception as exc:
            # Mark failure but let task-level autoretry handle transient problems
            try:
                CampaignSend.objects.filter(tenant=camp.tenant, campaign=camp, to_user_id=cust.id) \
                    .update(status="failed", error_message=str(exc))
            finally:
                raise

    return completed


# -------- orchestrator --------

@shared_task(bind=True)
def send_campaign_task(self, campaign_id: str, chunk_size: Optional[int] = None) -> dict:
    """
    Orchestrates a full campaign send: resolves audience → splits AB → chunks → schedules batches.
    Throttling is honored per campaign via `throttle_per_min`.
    Returns a small summary dict.
    """
    try:
        camp: Campaign = Campaign.objects.select_related("segment").get(id=campaign_id)
    except Campaign.DoesNotExist:
        return {"ok": False, "detail": "campaign not found"}

    if not camp.segment:
        return {"ok": False, "detail": "campaign has no segment"}

    # Resolve audience IDs once
    audience_qs = resolve_segment_queryset(camp.tenant, camp.segment.definition_json)
    ids = list(audience_qs.values_list("id", flat=True))
    total = len(ids)
    if total == 0:
        return {"ok": False, "detail": "segment empty", "total": 0}

    # Default chunk size & enforce bounds
    chunk_size = int(chunk_size or getattr(settings, "CAMPAIGN_DEFAULT_CHUNK_SIZE", 500))
    chunk_size = max(50, min(chunk_size, 5000))

    # AB split
    a_ids, b_ids = _split_ids_for_ab(ids, split=camp.ab_split)

    # Build batch schedule (ETA offsets) honoring throttle_per_min
    rate = int(camp.throttle_per_min or 0)

    plans: List[Tuple[List[str], BatchPlan]] = []
    eta_offset = 0

    def plan_side(side_ids: List[str], key: str):
        nonlocal eta_offset
        for batch in _chunked(side_ids, chunk_size):
            delay = _sec_for_batch(len(batch), rate)
            plans.append((batch, BatchPlan(size=len(batch), eta_offset_sec=eta_offset, variant_key=key)))
            eta_offset += delay

    plan_side(a_ids, "A")
    plan_side(b_ids, "B")

    # Update campaign state
    now = timezone.now()
    if camp.status not in ("sending", "completed"):
        camp.status = "sending"
        camp.started_at = camp.started_at or now
        camp.save(update_fields=["status", "started_at"])

    # Enqueue batches with per-batch ETA
    dispatched = 0
    for batch_ids, plan in plans:
        send_campaign_batch.apply_async(
            args=[str(camp.id), list(map(str, batch_ids)), plan.variant_key],
            countdown=plan.eta_offset_sec,
        )
        dispatched += plan.size

    # Naive completion schedule (optional): if there’s no throttle, we can set a completion ETA;
    # or you can have a beat task check for “all sends sent” and then mark completed.
    if rate == 0:
        # when we didn't add delays, flag it as completed optimistically
        camp.status = "completed"
        camp.completed_at = timezone.now()
        camp.save(update_fields=["status", "completed_at"])

    return {"ok": True, "planned": dispatched, "total": total, "chunks": len(plans), "throttle_per_min": rate}
