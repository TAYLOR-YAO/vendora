from django.utils import timezone
from django.db.models import Q
from rest_framework import permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import TenantScopedModelViewSet
from platformapp.permissions import IsTenantOperatorOrAdmin
from .models import Topic, NotificationTemplate, NotificationPreference, NotificationDispatch, NotificationLog
from .serializers import (
    TopicSerializer, NotificationTemplateSerializer, NotificationPreferenceSerializer,
    NotificationDispatchSerializer, NotificationLogSerializer
)
from .utils import queue_notification, render_preview
from .tasks import deliver_dispatch_async


READ_FILTERS = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


def _apply_q(request, qs, fields):
    q = request.query_params.get("q")
    if not q:
        return qs
    cond = Q()
    for f in fields:
        cond |= Q(**{f"{f}__icontains": q})
    return qs.filter(cond)


class TopicViewSet(TenantScopedModelViewSet):
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    permission_classes = [IsTenantOperatorOrAdmin | permissions.IsAuthenticated]
    filter_backends = READ_FILTERS
    search_fields = ["key", "name"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        return _apply_q(self.request, super().get_queryset(), self.search_fields)


class NotificationTemplateViewSet(TenantScopedModelViewSet):
    queryset = NotificationTemplate.objects.select_related("topic")
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsTenantOperatorOrAdmin | permissions.IsAuthenticated]
    filter_backends = READ_FILTERS
    search_fields = ["template_key", "locale", "channel", "subject", "body"]
    ordering_fields = ["template_key", "locale", "channel", "version", "created_at"]
    filterset_fields = ["template_key", "locale", "channel", "version", "is_active", "topic"]

    def get_queryset(self):
        return _apply_q(self.request, super().get_queryset(), self.search_fields)

    @action(detail=True, methods=["post"], url_path="preview", permission_classes=[IsTenantOperatorOrAdmin])
    def preview(self, request, pk=None):
        tmpl = self.get_object()
        payload = request.data.get("payload", {}) or {}
        rendered = render_preview(template=tmpl, payload=payload)
        return Response({"rendered": rendered})

    @action(detail=True, methods=["post"], url_path="deactivate", permission_classes=[IsTenantOperatorOrAdmin])
    def deactivate(self, request, pk=None):
        tmpl = self.get_object()
        tmpl.is_active = False
        tmpl.save(update_fields=["is_active"])
        return Response({"ok": True})


class NotificationPreferenceViewSet(TenantScopedModelViewSet):
    queryset = NotificationPreference.objects.select_related("topic", "template")
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]  # users may manage their own prefs
    filter_backends = READ_FILTERS
    search_fields = ["channel", "scope"]
    ordering_fields = ["created_at", "channel", "scope", "digest"]
    filterset_fields = ["user_id", "channel", "scope", "topic", "template", "is_enabled", "digest"]

    def get_queryset(self):
        qs = super().get_queryset()
        # If not operator/admin, restrict to requesting user only
        user = self.request.user
        if not (user and user.is_authenticated and IsTenantOperatorOrAdmin().has_permission(self.request, self)):
            qs = qs.filter(user_id=getattr(user, "id", None))
        return _apply_q(self.request, qs, self.search_fields)


class NotificationDispatchViewSet(TenantScopedModelViewSet):
    queryset = NotificationDispatch.objects.select_related("template", "topic").order_by("-created_at")
    serializer_class = NotificationDispatchSerializer
    permission_classes = [IsTenantOperatorOrAdmin | permissions.IsAuthenticated]
    filter_backends = READ_FILTERS
    search_fields = ["channel", "status", "to_address", "provider_ref"]
    ordering_fields = ["created_at", "sent_at", "status", "channel"]
    filterset_fields = ["channel", "status", "template", "topic", "to_user_id"]

    def get_queryset(self):
        return _apply_q(self.request, super().get_queryset(), self.search_fields)

    @action(detail=False, methods=["post"], url_path="queue", permission_classes=[IsTenantOperatorOrAdmin])
    def queue(self, request):
        """
        Body:
        {
          "template_id": "...",
          "to_user_id": "...", "to_address": "...",
          "channel": "email",
          "payload": {...},
          "schedule_at": "2025-10-04T10:00:00Z",
          "attachments": [{"url":"...","filename":"..."}]
        }
        """
        tenant = self.get_tenant(request)
        d = queue_notification(
            tenant=tenant,
            template_id=request.data.get("template_id"),
            topic_id=request.data.get("topic_id"),
            to_user_id=request.data.get("to_user_id"),
            to_address=request.data.get("to_address"),
            channel=request.data.get("channel", "email"),
            payload=request.data.get("payload") or {},
            schedule_at=request.data.get("schedule_at"),
            attachments=request.data.get("attachments") or [],
        )
        if not d.schedule_at:
            deliver_dispatch_async.delay(d.id)
        return Response(NotificationDispatchSerializer(d).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="send-now", permission_classes=[IsTenantOperatorOrAdmin])
    def send_now(self, request, pk=None):
        d = self.get_object()
        d.schedule_at = None
        d.status = "queued"
        d.save(update_fields=["schedule_at", "status"])
        deliver_dispatch_async.delay(d.id)
        return Response({"ok": True})

    @action(detail=True, methods=["post"], url_path="cancel", permission_classes=[IsTenantOperatorOrAdmin])
    def cancel(self, request, pk=None):
        d = self.get_object()
        if d.status in ("sent", "failed"):
            return Response({"detail": "Already finalized."}, status=400)
        d.status = "cancelled"
        d.save(update_fields=["status"])
        return Response({"ok": True})


class NotificationLogViewSet(TenantScopedModelViewSet):
    queryset = NotificationLog.objects.select_related("dispatch").order_by("-created_at")
    serializer_class = NotificationLogSerializer
    permission_classes = [IsTenantOperatorOrAdmin | permissions.IsAuthenticated]
    filter_backends = READ_FILTERS
    search_fields = ["provider", "status", "provider_ref"]
    ordering_fields = ["created_at", "status", "provider"]
    filterset_fields = ["dispatch", "status", "provider"]

    def get_queryset(self):
        return _apply_q(self.request, super().get_queryset(), self.search_fields)
