from typing import Dict, Any
from decimal import Decimal
import hmac, hashlib, json

from django.db.models import Q
from django.utils.timezone import now
from django.conf import settings

from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import TenantScopedModelViewSet, AuditedActionsMixin
from .models import (
    GatewayAccount, Payment, Refund, Payout, InstallmentPlan, Subscription, ProviderEvent
)
from .serializers import (
    GatewayAccountSerializer, PaymentSerializer, RefundSerializer,
    PayoutSerializer, InstallmentPlanSerializer, SubscriptionSerializer,
    ProviderEventSerializer
)
# adding "AuditedActionsMixin," before "TenantScopedModelViewSet" enables the audit logs

class PrivateReadWrite(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


# ---- Helpers ----

def _dec(v) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _idempotency_key(request) -> str | None:
    return request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key")


# ---- ViewSets ----

class GatewayAccountViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    """
    Private (auth required) – contains secrets/config.
    """
    queryset = GatewayAccount.objects.all().order_by("-created_at")
    serializer_class = GatewayAccountSerializer
    permission_classes = [PrivateReadWrite]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {"kind": ["exact","in"], "active": ["exact"], "region": ["exact"]}
    search_fields = ["display_name", "kind"]
    ordering_fields = ["created_at","kind","display_name","active"]
    ordering = ["-created_at"]


class PaymentViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    """
    Private (auth). Flexible filters + actions for init/confirm/refund/quote/webhook.
    """
    queryset = Payment.objects.select_related("order").order_by("-created_at")
    serializer_class = PaymentSerializer
    permission_classes = [PrivateReadWrite]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "status": ["exact", "in"],
        "provider": ["exact", "in"],
        "method": ["exact", "in"],
        "currency": ["exact"],
        "order_id": ["exact"],
    }
    search_fields = ["provider_ref", "provider_intent_id"]
    ordering_fields = ["created_at", "amount", "status", "provider"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(provider_ref__icontains=q)
                | Q(provider_intent_id__icontains=q)
                | Q(meta_json__icontains=q)
            )
        min_amount = self.request.query_params.get("min_amount")
        max_amount = self.request.query_params.get("max_amount")
        if min_amount:
            qs = qs.filter(amount__gte=_dec(min_amount))
        if max_amount:
            qs = qs.filter(amount__lte=_dec(max_amount))
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        # format: YYYY-MM-DD
        from django.utils.dateparse import parse_date
        if start:
            d = parse_date(start)
            if d:
                from django.utils.timezone import make_aware
                qs = qs.filter(created_at__gte=make_aware(d))
        if end:
            d = parse_date(end)
            if d:
                from django.utils.timezone import make_aware
                qs = qs.filter(created_at__lte=make_aware(d))
        return qs

    # --- Quotes/Fees (simple example) ---
    @action(detail=False, methods=["GET"], url_path="quote")
    def quote(self, request):
        """
        Example fee model:
          card: 2.9% + 100
          mobile_money: 1.2% + 50
          paypal: 3.4% + 100
        """
        method = request.query_params.get("method", "card")
        amount = _dec(request.query_params.get("amount") or "0")
        pct, flat = Decimal("0.029"), Decimal("100")
        if method == "mobile_money":
            pct, flat = Decimal("0.012"), Decimal("50")
        elif method == "paypal":
            pct, flat = Decimal("0.034"), Decimal("100")
        fee = (amount * pct).quantize(Decimal("0.01")) + flat
        return Response({"amount": str(amount), "fee": str(fee), "method": method})

    # --- Init (idempotent) ---
    @action(detail=False, methods=["POST"], url_path="init")
    def init(self, request):
        """
        Initialize a payment 'intent'.
        Body: { order, amount, currency, provider, method, phone?, payer_name?, idempotency_key? }
        Uses Idempotency-Key header if present to dedupe.
        """
        idem = _idempotency_key(request) or request.data.get("idempotency_key")
        payload = dict(request.data)
        # mobile money extras
        phone = payload.get("phone")
        provider = payload.get("provider") or "card"
        method = payload.get("method") or ("mobile_money" if phone else "card")
        flow = "server_confirm" if method != "paypal" else "redirect"

        # idempotency check
        if idem:
            existing = Payment.objects.filter(tenant=request.tenant, meta_json__idempotency_key=idem).first()
            if existing:
                return Response(PaymentSerializer(existing).data, status=status.HTTP_200_OK)

        payment = Payment.objects.create(
            tenant=request.tenant,
            order_id=payload.get("order"),
            amount=_dec(payload.get("amount")),
            currency=payload.get("currency") or "XOF",
            provider=provider,
            method=method,
            flow=flow,
            status="initiated",
            meta_json={
                "idempotency_key": idem,
                "phone": phone,
                "payer_name": payload.get("payer_name"),
                "source": "api",
            },
        )
        # Provider-specific bootstrap (mock):
        # For mobile money you might return a pay_code or USSD; for card a client_secret/redirect_url
        payment.client_secret = f"mock_{payment.id.hex[:10]}"
        payment.provider_intent_id = f"intent_{payment.id.hex[:8]}"
        payment.save(update_fields=["client_secret", "provider_intent_id"])

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    # --- Confirm/Capture ---
    @action(detail=True, methods=["POST"], url_path="confirm")
    def confirm(self, request, pk=None):
        """
        Confirm provider result (server webhook alternative if you poll client-side).
        Body could include provider payload; here we mock success/failure.
        """
        payment = self.get_object()
        outcome = request.data.get("outcome", "succeeded")  # "succeeded"|"failed"
        if outcome == "succeeded":
            payment.status = "succeeded"
            payment.paid_at = now()
            payment.captured_at = now()
            payment.failure_code = None
            payment.failure_message = None
        else:
            payment.status = "failed"
            payment.failure_code = request.data.get("failure_code") or "generic_error"
            payment.failure_message = request.data.get("failure_message") or "Payment failed"
        payment.save()
        return Response(PaymentSerializer(payment).data)

    # --- Refund (partial or full) ---
    @action(detail=True, methods=["POST"], url_path="refund")
    def refund(self, request, pk=None):
        payment = self.get_object()
        if not payment.is_refundable:
            return Response({"detail": "Payment is not refundable."}, status=status.HTTP_400_BAD_REQUEST)
        amount = _dec(request.data.get("amount") or (payment.amount - payment.refunded_amount))
        if amount <= 0:
            return Response({"detail": "Invalid refund amount."}, status=status.HTTP_400_BAD_REQUEST)
        new_total_refunded = payment.refunded_amount + amount
        if new_total_refunded > payment.amount:
            return Response({"detail": "Refund exceeds payment amount."}, status=status.HTTP_400_BAD_REQUEST)

        refund = Refund.objects.create(
            tenant=payment.tenant,
            payment=payment,
            amount=amount,
            status="pending",
            reason=request.data.get("reason"),
            meta_json={"requested_by": str(request.user.id)},
        )
        # Mock provider immediate success:
        refund.status = "succeeded"
        refund.provider_ref = f"rf_{refund.id.hex[:10]}"
        refund.save(update_fields=["status", "provider_ref"])

        payment.refunded_amount = new_total_refunded
        payment.status = "partially_refunded" if new_total_refunded < payment.amount else "refunded"
        payment.save(update_fields=["refunded_amount", "status"])

        return Response({
            "payment": PaymentSerializer(payment).data,
            "refund": RefundSerializer(refund).data
        }, status=status.HTTP_200_OK)

    # --- AI-ish filter assist ---
    @action(detail=False, methods=["GET"], url_path="search_assist")
    def search_assist(self, request):
        """
        e.g. ?query=failed last week over 100 mobile money
        """
        text = (request.query_params.get("query") or "").lower()
        filters: Dict[str, Any] = {}
        ordering = "-created_at"

        if "failed" in text: filters["status"] = "failed"
        if "succeeded" in text or "paid" in text: filters["status"] = "succeeded"
        if "mobile" in text: filters["method"] = "mobile_money"
        if "card" in text: filters["method"] = "card"
        if "paypal" in text: filters["provider"] = "paypal"

        import re
        over = re.search(r"over\s+(\d+(\.\d+)?)", text)
        under = re.search(r"under\s+(\d+(\.\d+)?)", text)
        if over: filters["min_amount"] = over.group(1)
        if under: filters["max_amount"] = under.group(1)

        # date shorthands
        from datetime import timedelta
        if "last week" in text:
            end = now()
            start = end - timedelta(days=7)
            filters["start"] = start.date().isoformat()
            filters["end"] = end.date().isoformat()

        return Response({"filters": filters, "ordering": ordering})

    # --- Webhook (AllowAny but HMAC verify) ---
    @action(detail=False, methods=["POST"], url_path="webhook", permission_classes=[])
    def webhook(self, request):
        """
        Generic webhook endpoint.
        Expect headers:
          X-Provider: stripe|tmoney|mtn|orange|fooz|paypal|bank|mock
          X-Webhook-Signature: HMAC hexdigest (optional if provider signs differently)
          X-Tenant-ID: tenant id to route to proper account (or include inside payload)
        """
        provider = request.headers.get("X-Provider", "mock")
        tenant = getattr(request, "tenant", None)  # your middleware might set this
        payload = request.data if isinstance(request.data, dict) else json.loads(request.body.decode() or "{}")
        signature = request.headers.get("X-Webhook-Signature")

        ga = GatewayAccount.objects.filter(tenant=tenant, kind=provider, active=True).first() if tenant else None
        if ga and ga.webhook_secret and signature:
            expected = hmac.new(ga.webhook_secret.encode(), msg=json.dumps(payload, separators=(",",":")).encode(), digestmod=hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, signature):
                return Response({"detail": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        # Save event
        ProviderEvent.objects.create(
            tenant=tenant,
            gateway_account=ga,
            provider=provider,
            event_type=str(payload.get("type") or payload.get("event") or "unknown"),
            payload=payload,
            signature=signature,
        )

        # Minimal demo: if payload conveys success, try to mark payment as succeeded
        provider_ref = payload.get("provider_ref") or payload.get("charge_id") or payload.get("txn_id")
        if provider_ref:
            p = Payment.objects.filter(tenant=tenant, provider=provider, provider_ref=provider_ref).first()
            if p and p.status not in ("succeeded", "refunded", "partially_refunded"):
                p.status = "succeeded"
                p.paid_at = now()
                p.save(update_fields=["status","paid_at"])

        return Response({"ok": True})
    

class RefundViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    queryset = Refund.objects.select_related("payment").order_by("-created_at")
    serializer_class = RefundSerializer
    permission_classes = [PrivateReadWrite]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {"status": ["exact","in"], "payment_id": ["exact"], "amount": ["gte","lte"]}
    search_fields = ["provider_ref", "reason"]
    ordering_fields = ["created_at","amount","status"]
    ordering = ["-created_at"]


class PayoutViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    queryset = Payout.objects.select_related("gateway_account").order_by("-created_at")
    serializer_class = PayoutSerializer
    permission_classes = [PrivateReadWrite]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {"status": ["exact","in"], "currency": ["exact"], "gateway_account_id": ["exact"]}
    search_fields = ["destination"]
    ordering_fields = ["created_at","amount","status"]
    ordering = ["-created_at"]


class InstallmentPlanViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    queryset = InstallmentPlan.objects.select_related("order").order_by("-created_at")
    serializer_class = InstallmentPlanSerializer
    permission_classes = [PrivateReadWrite]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {"status": ["exact","in"], "currency": ["exact"], "order_id": ["exact"]}
    search_fields = ["meta_json"]
    ordering_fields = ["created_at","total_amount","status"]
    ordering = ["-created_at"]

# adding "AuditedActionsMixin," before "TenantScopedModelViewSet" enables the audit logs
class SubscriptionViewSet(AuditedActionsMixin, TenantScopedModelViewSet):
    queryset = Subscription.objects.select_related("customer","gateway_account").order_by("-created_at")
    serializer_class = SubscriptionSerializer
    permission_classes = [PrivateReadWrite]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {"status": ["exact","in"], "plan_code": ["exact"], "currency": ["exact"]}
    search_fields = ["plan_code", "meta_json"]
    ordering_fields = ["created_at","amount","status","current_period_end"]
    ordering = ["-created_at"]
