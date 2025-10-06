from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.utils.dateparse import parse_datetime

from rest_framework import permissions, status, filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import TenantScopedModelViewSet
from platformapp.permissions import IsTenantOperatorOrAdmin
from notificationsapp.utils import queue_notification
from .tasks import send_campaign_task

from .models import Segment, Campaign, CampaignVariant, CampaignSend, CampaignEvent
from .serializers import (
    SegmentSerializer, CampaignSerializer, CampaignVariantSerializer,
    CampaignSendSerializer, CampaignEventSerializer
)
from .utils import resolve_segment_queryset


READ_FILTERS = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


def _q(request, qs, fields):
    q = request.query_params.get("q")
    if not q:
        return qs
    from django.db.models import Q as DQ
    cond = DQ()
    for f in fields:
        cond |= DQ(**{f"{f}__icontains": q})
    return qs.filter(cond)

# -------- Segments --------
class SegmentViewSet(TenantScopedModelViewSet):
    queryset = Segment.objects.all()
    serializer_class = SegmentSerializer
    permission_classes = [IsTenantOperatorOrAdmin]  # define/update segments: operators only
    filter_backends = READ_FILTERS
    search_fields = ["name"]
    ordering_fields = ["name", "approx_count", "updated_at"]
    filterset_fields = []

    def get_queryset(self):
        return _q(self.request, super().get_queryset(), self.search_fields)

    @action(detail=True, methods=["get"], permission_classes=[IsTenantOperatorOrAdmin])
    def preview(self, request, pk=None):
        seg = self.get_object()
        qs = resolve_segment_queryset(seg.tenant, seg.definition_json)
        limit = int(request.query_params.get("limit") or "20")
        rows = list(qs.values("id", "name", "email")[:limit])
        return Response({"count": qs.count(), "rows": rows})

    @action(detail=True, methods=["post"], permission_classes=[IsTenantOperatorOrAdmin])
    def refresh(self, request, pk=None):
        seg = self.get_object()
        qs = resolve_segment_queryset(seg.tenant, seg.definition_json)
        seg.approx_count = qs.count()
        seg.last_refreshed_at = timezone.now()
        seg.save(update_fields=["approx_count", "last_refreshed_at"])
        return Response({"ok": True, "approx_count": seg.approx_count})


# -------- Campaigns --------
class CampaignViewSet(TenantScopedModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    # Public GET for showing "published/completed" campaigns if you want a gallery (keep private for now)
    permission_classes = [IsTenantOperatorOrAdmin]
    filter_backends = READ_FILTERS
    search_fields = ["name", "subject", "content"]
    ordering_fields = ["created_at", "scheduled_at", "status", "name"]
    filterset_fields = ["status", "channel", "segment"]

    def get_queryset(self):
        return _q(self.request, super().get_queryset(), self.search_fields).prefetch_related("variants")

    @action(detail=True, methods=["post"], permission_classes=[IsTenantOperatorOrAdmin])
    def schedule(self, request, pk=None):
        camp: Campaign = self.get_object()
        at = request.data.get("scheduled_at")
        if not at:
            return Response({"detail": "scheduled_at is required ISO string"}, status=400)
        camp.scheduled_at = parse_datetime(at)
        camp.status = "scheduled"
        camp.save(update_fields=["scheduled_at", "status"])
        return Response({"ok": True})

    @action(detail=True, methods=["post"], permission_classes=[IsTenantOperatorOrAdmin])
    def pause(self, request, pk=None):
        camp: Campaign = self.get_object()
        if camp.status not in ("scheduled", "sending"):
            return Response({"detail": "Can pause only scheduled/sending campaigns"}, status=400)
        camp.status = "paused"
        camp.save(update_fields=["status"])
        return Response({"ok": True})

    @action(detail=True, methods=["post"], permission_classes=[IsTenantOperatorOrAdmin])
    def resume(self, request, pk=None):
        camp: Campaign = self.get_object()
        if camp.status != "paused":
            return Response({"detail": "Campaign is not paused"}, status=400)
        camp.status = "scheduled"
        camp.save(update_fields=["status"])
        return Response({"ok": True})

    @action(detail=True, methods=["post"], permission_classes=[IsTenantOperatorOrAdmin])
    def generate(self, request, pk=None):
        """
        AI-assist: generate subject/content from a brief.
        In production you could call your aiapp; here we stub a simple variant.
        Body: { "brief": "Promo for new sneakers", "variant_key": "B" }
        """
        camp = self.get_object()
        brief = (request.data.get("brief") or "").strip()
        key = (request.data.get("variant_key") or "B").upper()[:1]
        if not brief:
            return Response({"detail": "brief is required"}, status=400)

        # naive "generation"
        subject = f"🔥 {brief[:40]} — limited time!"
        content = f"<p>{brief}</p><p>Use code <b>WELCOME10</b> at checkout.</p>"

        var, _ = CampaignVariant.objects.update_or_create(
            tenant=camp.tenant, campaign=camp, key=key,
            defaults={"kind": "content", "subject": subject, "content": content, "is_active": True}
        )
        return Response({"ok": True, "variant": CampaignVariantSerializer(var).data})

    @action(detail=True, methods=["post"], permission_classes=[IsTenantOperatorOrAdmin])
    def send_now(self, request, pk=None):
        """
        Immediately fan-out CampaignSend rows and queue provider notifications.
        This is synchronous/small-batch; for large sends use a Celery task.
        """
        camp: Campaign = self.get_object()
        # optional override per call: {"chunk_size": 800}
        chunk_size = request.data.get("chunk_size")
        res = send_campaign_task.delay(str(camp.id), chunk_size)
        return Response({"ok": True, "task_id": res.id})

        # build audience
        audience_qs = resolve_segment_queryset(camp.tenant, seg.definition_json)
        count = audience_qs.count()
        if count == 0:
            return Response({"detail": "Segment empty"}, status=400)

        # light AB assignment
        split = max(0.0, min(1.0, camp.ab_split or 0.0))
        a_share = int(count * split)
        a_ids = set(list(audience_qs.values_list("id", flat=True)[:a_share]))
        now = timezone.now()

        # choose variant or fallback to campaign content
        vmap = {v.key.upper(): v for v in camp.variants.filter(is_active=True)}
        subj_default = camp.subject or ""
        content_default = camp.content or ""

        created = 0
        with transaction.atomic():
            if camp.status != "sending":
                camp.status = "sending"
                camp.started_at = now
                camp.save(update_fields=["status", "started_at"])

            for cust in audience_qs.only("id", "email", "name"):
                variant_key = "A" if cust.id in a_ids else "B"
                var = vmap.get(variant_key) or vmap.get("A") or None
                subject = (var.subject if var and var.subject else subj_default) or camp.name
                content = (var.content if var and var.content else content_default) or ""

                send = CampaignSend.objects.create(
                    tenant=camp.tenant,
                    campaign=camp,
                    variant_key=variant_key,
                    to_user_id=cust.id,
                    to_address=cust.email,
                    status="queued",
                )
                created += 1

                # enqueue through notificationsapp
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

            # naive completion
            camp.status = "completed"
            camp.completed_at = timezone.now()
            camp.save(update_fields=["status", "completed_at"])

        return Response({"ok": True, "created": created})

    @action(detail=True, methods=["get"], permission_classes=[IsTenantOperatorOrAdmin])
    def stats(self, request, pk=None):
        camp: Campaign = self.get_object()
        total = camp.sends.count()
        sent = camp.sends.filter(status="sent").count()
        failed = camp.sends.filter(status="failed").count()
        opens = camp.sends.aggregate(c=models.Sum("opens"))["c"] or 0
        clicks = camp.sends.aggregate(c=models.Sum("clicks"))["c"] or 0
        unsub = camp.sends.filter(unsubscribed=True).count()
        bounce = camp.sends.filter(bounced=True).count()
        return Response({
            "total": total, "sent": sent, "failed": failed,
            "opens": opens, "clicks": clicks, "unsubscribed": unsub, "bounced": bounce
        })


# -------- Sends (read-only) --------
class CampaignSendViewSet(TenantScopedModelViewSet):
    queryset = CampaignSend.objects.select_related("campaign").all().order_by("-created_at")
    serializer_class = CampaignSendSerializer
    permission_classes = [IsTenantOperatorOrAdmin]
    filter_backends = READ_FILTERS
    search_fields = ["to_address", "status", "provider_ref"]
    ordering_fields = ["created_at", "sent_at", "status"]
    filterset_fields = ["campaign", "status", "variant_key"]

    def get_queryset(self):
        return _q(self.request, super().get_queryset(), self.search_fields)


# -------- Events (ingest via webhook) --------
class CampaignEventViewSet(TenantScopedModelViewSet):
    queryset = CampaignEvent.objects.all().order_by("-created_at")
    serializer_class = CampaignEventSerializer
    permission_classes = [permissions.AllowAny]  # you will secure with a token in the body or header
    filter_backends = READ_FILTERS
    search_fields = ["event"]
    ordering_fields = ["created_at", "event"]
    filterset_fields = ["campaign", "event"]

    def create(self, request, *args, **kwargs):
        """
        Provider webhook:
        Body: { "token":"<shared>", "campaign_id":"...", "send_id":"...", "event":"open|click|..." }
        """
        shared = request.headers.get("X-Webhook-Token") or request.data.get("token")
        expected = (self.request.query_params.get("t") or "").strip()
        if expected and shared != expected:
            return Response({"detail": "Invalid token"}, status=403)

        tenant = self.get_tenant(request)
        camp_id = request.data.get("campaign_id")
        send_id = request.data.get("send_id")
        evt = (request.data.get("event") or "").lower()

        try:
            camp = Campaign.objects.get(tenant=tenant, id=camp_id)
        except Campaign.DoesNotExist:
            return Response({"detail": "Campaign not found"}, status=404)

        send = None
        if send_id:
            send = CampaignSend.objects.filter(tenant=tenant, id=send_id).first()

        obj = CampaignEvent.objects.create(
            tenant=tenant, campaign=camp, send=send, event=evt, meta_json=request.data
        )
        # update counters crudely
        if send:
            if evt == "open":
                send.opens += 1
            if evt == "click":
                send.clicks += 1
            if evt == "unsubscribe":
                send.unsubscribed = True
            if evt in ("bounce", "bounced"):
                send.bounced = True
            send.save(update_fields=["opens", "clicks", "unsubscribed", "bounced"])
        ser = self.get_serializer(obj)
        return Response(ser.data, status=201)
