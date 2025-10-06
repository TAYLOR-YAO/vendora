from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from common.mixins import TenantScopedModelViewSet
from .models import Plan, Price, Subscription, UsageRecord
from .serializers import PlanSerializer, PriceSerializer, SubscriptionSerializer, UsageRecordSerializer

class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Plan.objects.all().order_by("name")
    serializer_class = PlanSerializer
    filterset_fields = {"code": ["exact"]}
    search_fields = ["name","code"]

class PriceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Price.objects.select_related("plan").all()
    serializer_class = PriceSerializer
    filterset_fields = {"plan__code": ["exact"], "currency": ["exact"]}

class SubscriptionViewSet(TenantScopedModelViewSet):
    queryset = Subscription.objects.select_related("plan").all()
    serializer_class = SubscriptionSerializer
    filterset_fields = {"status": ["exact"], "plan__code": ["exact"]}

    @action(detail=False, methods=["post"])
    def record_usage(self, request):
        tenant = self.get_tenant(request)
        now = timezone.now()
        body = request.data or {}
        rec = UsageRecord.objects.create(
            tenant=tenant,
            metric=body.get("metric","api_calls"),
            quantity=int(body.get("quantity", 1)),
            window_start=now.replace(minute=0, second=0, microsecond=0),
            window_end=now.replace(minute=59, second=59, microsecond=0),
        )
        return Response({"ok": True, "id": str(rec.id)}, status=status.HTTP_201_CREATED)
