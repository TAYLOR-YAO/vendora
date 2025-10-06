# backend/aiapp/views.py
from __future__ import annotations

import os
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone
from django.db.models import Q

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.mixins import TenantScopedModelViewSet
from .models import AiModel, AiJob, AiPrediction, AiRecommendation
from .serializers import (
    AiModelSerializer,
    AiJobSerializer,
    AiPredictionSerializer,
    AiRecommendationSerializer,
)

# Try to import the “operator” permission, fall back to read-only admin if missing.
try:
    from .permissions import IsOperatorOrReadOnly as _Perm
except Exception:
    try:
        from .permissions import IsAdminOrReadOnly as _Perm  # fallback
    except Exception:
        from rest_framework.permissions import SAFE_METHODS, BasePermission
        class _Perm(BasePermission):  # very safe fallback
            def has_permission(self, request, view):
                return True if request.method in SAFE_METHODS else bool(request.user and request.user.is_staff)

# Optional ML deps (toggle with AIAPP_ENABLE_ML=false)
AIAPP_ENABLE_ML = os.getenv("AIAPP_ENABLE_ML", "true").lower() == "true"
SKLEARN_OK = False
if AIAPP_ENABLE_ML:
    try:
        from sklearn.metrics import roc_auc_score, average_precision_score
        from sklearn.linear_model import LogisticRegression  # noqa: F401 (used when training)
        SKLEARN_OK = True
    except Exception:
        SKLEARN_OK = False

# Analytics/Signals used by the fraud pack & recommender
try:
    from analyticsapp.models import RiskSignal, DeviceFingerprint, CoVisitEdge, ItemStat
except Exception:
    # If the analytics app isn’t ready yet, define no-op placeholders so the server still boots.
    RiskSignal = DeviceFingerprint = CoVisitEdge = ItemStat = None  # type: ignore

# Fraud feature pack (standardizer + rules)
try:
    from .features.fraud import extract_mobile_money_features, RiskRuleEngine
except Exception:
    # Minimal stubs so the server can run
    def extract_mobile_money_features(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "amount": float(payload.get("amount", 0) or 0),
            "currency": payload.get("currency", "XOF"),
            "device_fp": payload.get("device_fp") or payload.get("device_id"),
            "phone": payload.get("msisdn") or payload.get("phone"),
            "country": payload.get("country", "TG"),
            "hour": int(payload.get("hour", timezone.now().hour)),
        }

    class RiskRuleEngine:
        def score(self, feats: Dict[str, Any], device_usage: int = 1):
            # Tiny neutral default: everything scores 0.1
            return 0.1, ["default_stub"], "low"


# ---- small helpers ----------------------------------------------------------

def _ml_required() -> Optional[Response]:
    """Return a 501 response if sklearn isn’t available/enabled."""
    if not SKLEARN_OK:
        return Response(
            {"detail": "ML features are disabled or scikit-learn is not installed."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
    return None


def _load_fraud_artifacts(tenant_id) -> Optional[Tuple[Any, Any]]:
    """
    Load vectorizer/model from your artifact store (FS/DB/Cloud Storage).
    For now this returns None so we fall back to rules unless you wire it up.
    Return (vectorizer, model) when available.
    """
    return None


# ---- ViewSets ---------------------------------------------------------------

class AiModelViewSet(TenantScopedModelViewSet):
    """
    - Standard CRUD for AI models
    - /train    → enqueue a training job (Celery)
    - /infer    → synchronous inference pass-through
    - /recommend → synchronous recommend pass-through
    - /fraud/features → normalize provider payload into features
    - /fraud/metrics  → compute ROC/PR on recent labels
    - /fraud/score    → fast rules+features score for mobile-money/card
    - /recommend/content → co-visitation + popularity fallback
    """
    queryset = AiModel.objects.all().order_by("-updated_at")
    serializer_class = AiModelSerializer
    permission_classes = [_Perm]
    # Valid fields on AiModel: name, version, task, is_active
    filterset_fields = {"task": ["exact"], "is_active": ["exact"]}
    search_fields = ["name", "version"]

    # --- Train / Infer / Recommend ------------------------------------------

    @action(detail=True, methods=["post"], url_path="train")
    def train(self, request, pk=None):
        # Keep it simple: create a job row. If you wired Celery, enqueue there.
        m = self.get_object()
        job = AiJob.objects.create(
            tenant=m.tenant or self.get_tenant(request),
            model=m,
            job_type=AiJob.JobType.TRAIN,
            entity_type="model",
            entity_id=m.id,
            input_json=request.data or {},
            status=AiJob.JobStatus.QUEUED,
        )
        # If you have Celery: from .tasks import run_job_task; run_job_task.delay(job.id)
        return Response({"job_id": job.id, "status": job.status}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="infer")
    def infer(self, request, pk=None):
        m = self.get_object()
        # Plug your provider abstraction here if you have it; for now echo input
        payload = request.data or {}
        return Response({"model": m.id, "echo": payload}, status=200)

    @action(detail=True, methods=["post"], url_path="recommend")
    def recommend(self, request, pk=None):
        m = self.get_object()
        payload = request.data or {}
        return Response({"model": m.id, "echo": payload}, status=200)

    # --- Fraud pack ----------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="fraud/features")
    def fraud_features(self, request, pk=None):
        """
        Standardize provider payload → normalized features.
        Accepts arbitrary payment/checkout payload (card, mobile money, etc.).
        """
        tenant = self.get_tenant(request)
        payload = request.data or {}
        feats = extract_mobile_money_features(payload)
        # optional: record device fingerprint heat
        try:
            if DeviceFingerprint and (fp := feats.get("device_fp")):
                DeviceFingerprint.objects.get_or_create(tenant=tenant, fp=fp)
        except Exception:
            pass
        return Response({"features": feats}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="fraud/metrics")
    def fraud_metrics(self, request, pk=None):
        """
        Compute ROC-AUC & PR-AUC on a recent validation slice.

        Query params:
        - days: int (default 30)
        - use: 'ml'|'rules'|'auto' (default 'auto')
        """
        from payments.models import Payment

        tenant = self.get_tenant(request)
        days = int(request.query_params.get("days", "30"))
        strategy = (request.query_params.get("use") or "auto").lower()
        since = timezone.now() - timedelta(days=days)

        # 1) Ground truth from payments within the window
        good = {"succeeded", "paid", "authorized", "captured"}
        bad = {"chargeback", "refunded", "failed", "blocked"}

        payments = list(
            Payment.objects.filter(tenant=tenant, created_at__gte=since).values("id", "status")
        )

        y: List[int] = []
        ids: List[str] = []
        for p in payments:
            st = (p["status"] or "").lower()
            if st in good:
                y.append(0)
                ids.append(str(p["id"]))
            elif st in bad:
                y.append(1)
                ids.append(str(p["id"]))

        if not y:
            return Response({"ok": False, "reason": "no_labels_in_window"}, status=200)

        # 2) Try ML scores first (if artifacts exist and strategy != 'rules')
        artifacts = None
        if strategy in ("ml", "auto"):
            artifacts = _load_fraud_artifacts(tenant.id)

        scores: List[float] = []
        if artifacts and SKLEARN_OK and RiskSignal is not None:
            vec, mdl = artifacts
            # batch transform for speed using recorded features
            feats_by_id = {}
            for s in RiskSignal.objects.filter(
                tenant=tenant, entity_type="payment", entity_id__in=ids
            ).values("entity_id", "features"):
                feats_by_id[str(s["entity_id"])] = s.get("features") or {}

            X = [feats_by_id.get(i, {}) for i in ids]
            if any(X):
                Xv = vec.transform(X)
                import numpy as _np  # local import
                probs = mdl.predict_proba(Xv)[:, 1]
                scores = _np.asarray(probs, dtype=float).tolist()
            else:
                artifacts = None  # fallback if we have no features

        # 3) Fallback: rules-only score from recorded RiskSignals (or neutral 0.5)
        if not scores:
            if RiskSignal is not None:
                score_map = {
                    str(s["entity_id"]): float(s.get("score") or 0.0)
                    for s in RiskSignal.objects.filter(
                        tenant=tenant, entity_type="payment", entity_id__in=ids
                    ).values("entity_id", "score")
                }
                scores = [score_map.get(pid, 0.5) for pid in ids]
            else:
                scores = [0.5] * len(ids)

        # 4) AUC metrics (guard if sklearn missing)
        roc = pr = None
        if SKLEARN_OK:
            try:
                roc = float(roc_auc_score(y, scores))
            except Exception:
                roc = None
            try:
                pr = float(average_precision_score(y, scores))
            except Exception:
                pr = None

        return Response(
            {
                "ok": True,
                "window_days": days,
                "n_labels": len(y),
                "n_pos": int(sum(y)),
                "n_neg": int(len(y) - sum(y)),
                "strategy": ("ml" if artifacts and strategy != "rules" else "rules"),
                "roc_auc": roc,
                "pr_auc": pr,
            },
            status=200,
        )

    @action(detail=True, methods=["post"], url_path="fraud/score")
    def fraud_score(self, request, pk=None):
        """
        Synchronous mobile-money fraud risk score using feature pack + rules.
        Pass transaction payload; returns score/bucket & rules_hit.
        """
        tenant = self.get_tenant(request)
        payload = request.data or {}
        feats = extract_mobile_money_features(payload)

        # optional device heat (how many customers share it in last 90d)
        device_usage = 1
        try:
            if DeviceFingerprint and (fp := feats.get("device_fp")):
                device_usage = (
                    DeviceFingerprint.objects.filter(tenant=tenant, fp=fp).count() or 1
                )
        except Exception:
            pass

        engine = RiskRuleEngine()
        score, rules_hit, bucket = engine.score(feats, device_usage)

        # persist a signal (best-effort)
        try:
            if RiskSignal is not None:
                RiskSignal.objects.create(
                    tenant=tenant,
                    entity_type="payment",
                    entity_id=payload.get("payment_id"),
                    score=score,
                    bucket=bucket,
                    rules_hit=rules_hit,
                    features=feats,
                )
        except Exception:
            pass

        return Response(
            {"score": float(score), "bucket": bucket, "rules_hit": rules_hit, "features": feats},
            status=200,
        )

    # --- Content recommender -------------------------------------------------

    @action(detail=True, methods=["post"], url_path="recommend/content")
    def recommend_content(self, request, pk=None):
        """
        Hybrid content-based: co-visitation from recent items + fallback to popularity.
        Payload: { "recent": ["prodA","prodB"], "k": 12, "exclude": ["..."] }
        """
        tenant = self.get_tenant(request)
        body = request.data or {}
        recent: List[str] = body.get("recent") or []
        k = int(body.get("k", 12))
        exclude = set(map(str, (body.get("exclude") or []))) | set(recent)

        items: List[str] = []

        # 1) Gather neighbors by co-visitation
        if CoVisitEdge is not None and recent:
            cand_scores: Dict[str, float] = {}
            for r in recent[:5]:
                for edge in CoVisitEdge.objects.filter(tenant=tenant, item_a=r).order_by("-weight")[:200]:
                    if edge.item_b in exclude:
                        continue
                    cand_scores[edge.item_b] = cand_scores.get(edge.item_b, 0.0) + float(edge.weight or 0)
                for edge in CoVisitEdge.objects.filter(tenant=tenant, item_b=r).order_by("-weight")[:200]:
                    if edge.item_a in exclude:
                        continue
                    cand_scores[edge.item_a] = cand_scores.get(edge.item_a, 0.0) + float(edge.weight or 0)

            ranked = sorted(cand_scores.items(), key=lambda x: x[1], reverse=True)
            items = [i for i, _ in ranked[:k]]

        # 2) Fallback with popularity if not enough
        if len(items) < k and ItemStat is not None:
            missing = k - len(items)
            pops = (
                ItemStat.objects.filter(tenant=tenant)
                .exclude(item_id__in=exclude | set(items))
                .order_by("-popularity")[:missing]
            )
            items.extend([p.item_id for p in pops])

        return Response({"items": items}, status=200)


class AiJobViewSet(TenantScopedModelViewSet):
    queryset = AiJob.objects.all().order_by("-created_at")
    serializer_class = AiJobSerializer
    permission_classes = [_Perm]
    filterset_fields = {"model": ["exact"], "job_type": ["exact"], "status": ["exact"]}
    search_fields = ["entity_type"]

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        job = self.get_object()
        # Minimal state machine
        if job.status in (AiJob.JobStatus.COMPLETED, AiJob.JobStatus.FAILED):
            return Response({"detail": "Job already finished"}, status=400)
        job.status = AiJob.JobStatus.FAILED
        job.output_json = {"cancelled": True}
        job.save(update_fields=["status", "output_json"])
        return Response({"ok": True})


class AiPredictionViewSet(TenantScopedModelViewSet):
    queryset = AiPrediction.objects.all().order_by("-created_at")
    serializer_class = AiPredictionSerializer
    permission_classes = [_Perm]
    filterset_fields = {"model": ["exact"], "entity_type": ["exact"]}
    search_fields = ["entity_type"]


class AiRecommendationViewSet(TenantScopedModelViewSet):
    queryset = AiRecommendation.objects.all().order_by("-created_at")
    serializer_class = AiRecommendationSerializer
    permission_classes = [_Perm]
    filterset_fields = {"model": ["exact"], "customer": ["exact"], "context": ["exact"]}
    search_fields = ["context"]


# ---- Webhook for async providers (optional) --------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
def provider_webhook(request):
    """
    Providers can POST updates here: {job_id, status, output, error}
    You’ll map this URL in urls.py and share with HTTP providers.
    """
    jid = request.data.get("job_id")
    if not jid:
        return Response({"detail": "job_id required"}, status=400)
    try:
        job = AiJob.objects.get(id=jid)
    except AiJob.DoesNotExist:
        return Response({"detail": "job not found"}, status=404)

    status_ = str(request.data.get("status", "")).lower()
    if status_ in ("completed", "done", "ok"):
        job.status = AiJob.JobStatus.COMPLETED
        job.output_json = request.data.get("output") or {}
        job.save(update_fields=["status", "output_json"])
    elif status_ in ("failed", "error"):
        job.status = AiJob.JobStatus.FAILED
        job.output_json = {"error": request.data.get("error", "unknown")}
        job.save(update_fields=["status", "output_json"])
    elif status_ in ("running", "processing"):
        job.status = AiJob.JobStatus.RUNNING
        job.save(update_fields=["status"])
    # else ignore unknown transitions

    return Response({"ok": True})
